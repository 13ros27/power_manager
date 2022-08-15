"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from handlers import ChangeHandler, LiveStatusHandler
from nvi import NonVolatileInformation
from pathlib import Path
from state import Mode, Modes
from telegram import Update
from telegram.error import NetworkError
from telegram.ext import CallbackQueryHandler, CommandHandler, Updater, CallbackContext
from quasar import Quasar

class Info:
    def __init__(self):
        self.info = {}
        self.last_info = {}

    def get(self, *items, require=False):
        stuff = [self.info.get(item) for item in items]
        if require and list(filter(lambda x: x is None, stuff)) != []:
            return None
        else:
            return stuff

    def update(self, new_info: dict):
        self.last_info = self.info
        self.info = new_info

    def item_has_changed(self, item: str):
        return self.info.get(item) != self.last_info.get(item)

    def __getitem__(self, item):
        return self.info.get(item)

def update_settings(f):
    def wrapper(self, update: Update, *args, **kwargs):
        f(self, update, *args, **kwargs)
        if isinstance(self, TelegramBot):
            tbot = self
        else:
            tbot = self.tbot
        chat_id = tbot.get_chat_id(update)
        if tbot.last_settings.get(chat_id) is not None:
            mes_id = tbot.send_text(tbot.settings_text(), chat_id).message_id
            tbot.delete_message(chat_id, tbot.last_settings[chat_id])
            tbot.last_settings[chat_id] = mes_id
    return wrapper

class TelegramBot:
    """Control all the aspects of the telegram bot side of it."""

    def __init__(self, config: Config, modes: Modes, quasar: Quasar):
        """Set up the necessary functions and operations."""
        self.charge_vals = [('Free', 0.0), ('Below Off Peak', config.low_night), ('Above Off Peak', config.high_night),
                            ('Below Peak', config.low_day), ('Above Peak', config.high_day)]
        self.discharge_vals = [('Free', 0.0), ('Off Peak', config.discharge_rate), ('Below Peak', config.low_day)]
        self.config = config
        self.modes = modes
        self.quasar = quasar
        self.logger = config.logger
        self.nvinfo = NonVolatileInformation(config.path / Path('telegram_info.json'))
        self.updater = Updater(self.nvinfo.token)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(CallbackQueryHandler(self.button))
        self.dispatcher.add_error_handler(self.error_handler)
        self.change_handlers = []
        self.info = Info()
        self.last_settings = {}
        self.updater.start_polling()

    def error_handler(self, _: object, context: CallbackContext):
        self.logger.error(f'Error handling: {context.error}')

    def add_command(self, name: str, func):
        self.dispatcher.add_handler(CommandHandler(name, func))

    def add_chat(self, update: Update):
        if update.effective_chat is not None:
            self.nvinfo.add_chat(update.effective_chat.id)
        self.logger.warning('Could not add member to chat')

    def second_item(self, update: Update, default=None, error='Internal Error') -> str:
        sp = update.message.text.split(' ')
        if len(sp) >= 2:
            return sp[1]
        else:
            if default is None:
                self.reply_text(update, error)
                return ''
            else:
                return default

    def add_handler(self, handler: ChangeHandler):
        self.change_handlers.append(handler)

    def remove_handler(self, handler):
        handler.remove()
        del self.change_handlers[self.change_handlers.index(handler)]

    def get_chat_id(self, update: Update):
        if update.effective_chat is not None:
            return update.effective_chat.id
        else:
            raise TypeError('update.effective_chat is None')

    def _send(self, command, *args, **kwargs):
        try:
            self.logger.info(f'{command}({", ".join(map(str, args))}, {kwargs})')
            return command(*args, **kwargs)
        except NetworkError:
            self.logger.warning('Network Error')
        except:  # noqa
            self.logger.exception('Telegram Bot:')

    def reply_text(self, update: Update, text: str, **kwargs):
        """Reply with a text message, with error handling."""
        return self._send(update.message.reply_text, text, **kwargs)

    def reply_document(self, update: Update, filepath: Path, **kwargs):
        """Reply with a document from a particular filepath."""
        return self._send(update.message.reply_document, open(filepath, 'rb'), **kwargs)

    def send_text(self, text: str, chat_id: int, silent=False, **kwargs):
        """Send a text message to a given chat."""
        return self._send(self.updater.bot.send_message, chat_id, text, disable_notification=silent, **kwargs)

    def edit_message_text(self, text: str, chat_id: int, mes_id: int, **kwargs):
        """Edit a given message."""
        return self._send(self.updater.bot.edit_message_text, text, chat_id, mes_id, **kwargs)

    def delete_message(self, chat_id: int, mes_id: int, **kwargs):
        """Delete a given message."""
        return self._send(self.updater.bot.delete_message, chat_id, mes_id, **kwargs)

    def formatted_current(self, rounding: int = 1, kw: bool = False):
        info = self.info.get('currents', 'estimated', 'recommended', 'charge_rate', require=True)
        if info is None:
            message = 'N/A'
        else:
            (currents, estimated, recommended, charge_rate) = info
            if kw:
                multiplier = 0.24
                symbol = 'kW'
            else:
                multiplier = 1
                symbol = 'A'
            message = []
            if currents is None or estimated is None:
                raise TypeError('Unreachable')
            for (name, ct, current) in zip(self.config.names, self.config.current_types, currents):
                message.append(f'{round(current * multiplier, rounding)}{symbol}: {name} ({ct.name})')
            if not kw:
                message.append(f'{round(estimated, rounding)}A: Estimated')
                message.append(f'{recommended}A: Recommended')
                message.append(f'{charge_rate}A: Charge Rate')
                soc = self.quasar.soc
                if soc == 0:
                    message.append('?%: State of Charge')
                else:
                    message.append(f'{self.quasar.soc}%: State of Charge')
            message = '\n'.join(message)
        return message

    def update_info(self, currents: list, estimated: float, recommended: int, charge_rate: int):
        """Update what it knows about the state."""
        self.info.update({'currents': currents, 'estimated': estimated, 'recommended': recommended, 'charge_rate': charge_rate})
        for handler in self.change_handlers:
            if handler.should_update():
                if handler.update() is False:
                    self.remove_handler(handler)

    def button(self, update: Update, _):
        """Run the continue button from LiveStatus.update."""
        query = update.callback_query
        query.answer()
        data = query.data.strip().split(' ')
        if len(data) == 2:
            chat_id = int(data[0])
            mes_id = int(data[1])
            self.add_handler(LiveStatusHandler(self, chat_id, 300, mes_id))
        elif len(data) == 4:
            self.button_menus(update, data)
        else:
            raise TypeError(f'Did not expect {data}')

    @update_settings
    def button_menus(self, _: Update, data: list):
        chat_id = int(data[0])
        mes_id = int(data[1])
        menu_type = int(data[2])
        mode_value = round(float(data[3]), 1)
        if menu_type == 0:
            self.modes.user_settings.charge_cost_limit = mode_value
            self.edit_message_text(f'The charge cost limit has been changed to {mode_value}p', chat_id, mes_id)
        elif menu_type == 1:
            self.modes.user_settings.discharge_value = mode_value
            self.edit_message_text(f'The discharge value has been changed to {mode_value}p', chat_id, mes_id)
        elif menu_type == 2:
            self.modes.set_mode(Mode(int(mode_value)))
            self.edit_message_text(f'The user mode has been changed to {Mode(int(mode_value)).name}', chat_id, mes_id)
        else:
            raise ValueError(f'Did not expect menu_type \'{menu_type}\'')

    def cost_text(self, cost: float, known: list):
        text = f'{cost}p'
        for (name, val) in known:
            if val == cost:
                name_text = ''.join([w[0] for w in name.replace('Below', '<').replace('Above', '>').split(' ')])
                text = f'({name_text}) {text}'
                break
        return text

    def settings_text(self) -> str:
        us = self.modes.user_settings
        return f'''/user_mode {self.modes._mode.name}
/charge_cost_limit {self.cost_text(us.charge_cost_limit, self.charge_vals)}
/discharge_value {self.cost_text(us.discharge_value, self.discharge_vals)}
/max_paid_soc {None if us.max_paid_soc == -1 else str(us.max_paid_soc) + '%'}
/min_discharge_soc {None if us.min_discharge_soc == -1 else str(us.min_discharge_soc) + '%'}'''

    def cleanup(self):
        """Kills all handlers."""
        for handler in self.change_handlers:
            self.remove_handler(handler)
