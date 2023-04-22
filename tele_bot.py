"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from datalogger import DataLogger
from handlers import ChangeHandler, LiveStatusHandler
from nvi import NonVolatileInformation
from pathlib import Path
from state import Mode, Modes
from telegram import Update
from telegram.error import NetworkError
from telegram.ext import (CallbackQueryHandler, CommandHandler, MessageHandler,
                          Updater, CallbackContext, Filters)
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

class TelegramBot:
    """Control all the aspects of the telegram bot side of it."""

    def __init__(self, config: Config, datalogger: DataLogger, start_mode: Mode, quasar: Quasar):
        """Set up the necessary functions and operations."""
        self.charge_vals = [
            ('Free', 0.0), ('Below Off Peak', config.low_night),
            ('Above Off Peak', config.high_night), ('Below Peak', config.low_day),
            ('Above Peak', config.high_day), ('Custom', -1.0)
        ]
        self.discharge_vals = [
            ('Free', (0.0, 0.0)), ('Off Peak', (config.discharge_rate, config.discharge_rate)),
            ('Low Export', (config.discharge_rate, (config.discharge_rate + config.low_day) / 2)),
            ('Below Peak', (config.low_day, config.low_day)), ('Custom', (-1.0, -1.0))
        ]
        self.config = config
        self.datalogger = datalogger
        self.quasar = quasar
        self.logger = config.logger
        self.nvinfo = NonVolatileInformation(config.path / Path('telegram_info.json'))
        self.modes = Modes(config, start_mode, self.nvinfo, quasar)
        self.updater = Updater(self.nvinfo.token)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(CallbackQueryHandler(self.button))
        self.dispatcher.add_error_handler(self.error_handler)
        self.dispatcher.add_handler(
            MessageHandler(Filters.text & (~Filters.command), self.message_handler))
        self.change_handlers = []
        self.info = Info()
        self.last_settings = {}
        self.updater.start_polling()
        self.particular_message_handler = None

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

    def _send(self, command, *args, mes_id = False, **kwargs):
        try:
            self.logger.info(f'{command}({", ".join(map(str, args))}, {kwargs})')
            ret = command(*args, **kwargs)
            if mes_id:
                if ret is not None:
                    return ret.message_id
                else:
                    raise TypeError('Expected message id')
            else:
                return ret
        except NetworkError:
            self.logger.warning('Network Error')
        except:  # noqa
            self.logger.exception('Telegram Bot:')

    def reply_text(self, update: Update, text: str, **kwargs) -> int:
        """Reply with a text message, with error handling."""
        ret = self._send(update.message.reply_text, text, **kwargs, mes_id = True)
        if isinstance(ret, int):
            return ret
        else:
            raise TypeError('Unreachable')

    def reply_document(self, update: Update, filepath: Path, **kwargs):
        """Reply with a document from a particular filepath."""
        return self._send(update.message.reply_document, open(filepath, 'rb'), **kwargs)

    def send_text(self, text: str, chat_id: int, silent=False, **kwargs):
        """Send a text message to a given chat."""
        return self._send(self.updater.bot.send_message, chat_id, text,
                          disable_notification=silent, **kwargs)

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
        self.info.update({'currents': currents, 'estimated': estimated,
                          'recommended': recommended, 'charge_rate': charge_rate})
        for handler in self.change_handlers:
            if handler.should_update():
                if handler.update() is False:
                    self.remove_handler(handler)

    def button(self, update: Update, _):
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

    def update_settings(self, update: Update):
        chat_id = self.get_chat_id(update)
        if self.last_settings.get(chat_id) is not None:
            mes = self.send_text(self.settings_text(), chat_id)
            if mes is None:
                raise TypeError('Expected message id')
            mes_id = mes.message_id
            self.delete_message(chat_id, self.last_settings[chat_id])
            self.last_settings[chat_id] = mes_id

    def button_menus(self, update: Update, data: list):
        updated = True
        chat_id = int(data[0])
        mes_id = int(data[1])
        menu_type = int(data[2])
        if menu_type == 0:
            mode_value = round(float(data[3]), 1)
            if mode_value == -1.0:
                updated = False
                self.particular_message_handler = (self._change_charge_cost_limit, self.get_chat_id(update))
                self.edit_message_text('Please enter a charge cost limit:', chat_id, mes_id)
            else:
                text, success = self._change_charge_cost_limit(mode_value)
                updated = success
                self.edit_message_text(text, chat_id, mes_id)
                self.datalogger.add_metadata(text)
        elif menu_type == 1:
            vals = data[3].split('_')
            dis_val = round(float(vals[0]), 1)
            ldis_val = round(float(vals[1]), 1)
            if dis_val == -1.0:
                updated = False
                self.particular_message_handler = (self._change_discharge_value, self.get_chat_id(update))
                self.edit_message_text('Please enter a discharge value:', chat_id, mes_id)
            else:
                if dis_val != ldis_val:
                    change = f'{dis_val}p [{ldis_val}p]'
                else:
                    change = f'{dis_val}'
                self.modes.user_settings.discharge_value = dis_val
                self.modes.user_settings.low_discharge_value = ldis_val
                self.edit_message_text(f'The discharge value has been changed to {change}',
                                       chat_id, mes_id)
                self.datalogger.add_metadata(f'The discharge value has been changed to {change}')
        elif menu_type == 2:
            mode_value = int(data[3])
            self.modes.set_mode(Mode(mode_value))
            self.edit_message_text(f'The user mode has been changed to {Mode(mode_value).name}',
                                   chat_id, mes_id)
            self.datalogger.add_metadata(f'The user mode has been changed to {Mode(mode_value).name}')
        elif menu_type == 3:
            if int(data[3]) == -1:
                updated = False
                self.particular_message_handler = (self._change_max_paid_soc, self.get_chat_id(update))
                self.edit_message_text('Please enter a max paid SoC:', chat_id, mes_id)
            else:
                text, success = self._change_max_paid_soc(data[3])
                updated = success
                self.edit_message_text(text, chat_id, mes_id)
                self.datalogger.add_metadata(text)
        elif menu_type == 4:
            if int(data[3]) == -1:
                updated = False
                self.particular_message_handler = (self._change_min_discharge_soc, self.get_chat_id(update))
                self.edit_message_text('Please enter a min discharge SoC:', chat_id, mes_id)
            else:
                text, success = self._change_min_discharge_soc(data[3])
                updated = success
                self.edit_message_text(text, chat_id, mes_id)
                self.datalogger.add_metadata(text)
        else:
            raise ValueError(f'Did not expect menu_type \'{menu_type}\'')
        if updated:
            self.update_settings(update)

    def _change_charge_cost_limit(self, value) -> tuple:
        try:
            new_value = float(value)
            self.modes.user_settings.charge_cost_limit = new_value
            return (f'The charge cost limit has been changed to {new_value}p', True)
        except ValueError:
            return ('Please enter a float:', False)

    def _change_discharge_value(self, value) -> tuple:
        try:
            new_value = float(value)
            self.modes.user_settings.discharge_value = new_value
            self.modes.user_settings.low_discharge_value = new_value
            return (f'The discharge value has been changed to {new_value}p', True)
        except ValueError:
            return ('Please enter a float:', False)

    def _change_max_paid_soc(self, value) -> tuple:
        try:
            new_value = int(value)
            self.modes.user_settings.max_paid_soc = new_value
            return (f'The max paid SoC has been changed to {new_value}%, the current SoC is {self.quasar.soc}%', True)
        except ValueError:
            return ('Please enter an integer:', False)

    def _change_min_discharge_soc(self, value) -> tuple:
        try:
            new_value = int(value)
            self.modes.user_settings.min_discharge_soc = new_value
            return (f'The min discharge SoC has been changed to {new_value}%, the current SoC is {self.quasar.soc}%', True)
        except ValueError:
            return ('Please enter an integer:', False)

    def cost_text(self, cost, known: list):
        if isinstance(cost, tuple):
            if cost[0] == cost[1]:
                text = f'{cost[0]}p'
            else:
                text = f'{cost[0]}p [{cost[1]}p]'
        else:
            text = f'{cost}p'
        for (name, val) in known:
            if val == cost:
                name_text = ''.join([w[0] for w in
                                     name.replace('Below', '<').replace('Above', '>').split(' ')])
                text = f'({name_text}) {text}'
                break
        return text

    def settings_text(self) -> str:
        us = self.modes.user_settings
        return f'''\
/user_mode {self.modes._mode.name}
/charge_cost_limit {self.cost_text(us.charge_cost_limit, self.charge_vals)}
/discharge_value {self.cost_text((us.discharge_value, us.low_discharge_value), self.discharge_vals)}
/max_paid_soc {None if us.max_paid_soc == -1 else str(us.max_paid_soc) + '%'}
/min_discharge_soc {None if us.min_discharge_soc == -1 else str(us.min_discharge_soc) + '%'}'''

    def message_handler(self, update: Update, _: CallbackContext):
        if self.particular_message_handler is None:
            return None
        elif update.effective_chat.id == self.particular_message_handler[1]:
            m_handler = self.particular_message_handler[0]
            text, success = m_handler(update.message.text)
            self.reply_text(update, text)
            if success:
                self.particular_message_handler = None
                self.update_settings(update)

    def cleanup(self):
        """Kills all handlers."""
        for handler in self.change_handlers:
            self.remove_handler(handler)
