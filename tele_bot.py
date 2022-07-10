"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from handlers import LiveStatusHandler
from nvi import NonVolatileInformation
from pathlib import Path
from telegram import Update
from telegram.error import NetworkError
from telegram.ext import CallbackQueryHandler, CommandHandler, Updater

class TelegramBot:
    """Control all the aspects of the telegram bot side of it."""

    def __init__(self, config: Config):
        """Set up the necessary functions and operations."""
        self.config = config
        self.logger = config.logger
        self.nvinfo = NonVolatileInformation(config.path / Path('telegram_info.json'))
        self.updater = Updater(self.nvinfo.token)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(CallbackQueryHandler(self.button))
        self.change_handlers = [[], [], []]
        self.info = (None, None, None)
        self.last_info = (None, None, None)
        self.last_recommendations = {}
        self.following = False
        self.updater.start_polling()

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

    def add_handler(self, handler):
        for i in handler.updates_on():
            self.change_handlers[i].append(handler)

    def remove_handler(self, handler):
        handler.remove()
        for (i, handlers) in enumerate(self.change_handlers):
            if handler in handlers:
                del self.change_handlers[i][handlers.index(handler)]

    def get_chat_id(self, update: Update):
        if update.effective_chat is not None:
            return update.effective_chat.id
        else:
            raise TypeError('update.effective_chat is None')

    def _send(self, command, *args, **kwargs):
        try:
            self.logger.info(f'{command}({", ".join(map(str, args))}, {kwargs})')
            return command(*args, **kwargs)
        # except NetworkError:
        #     self.logger.warning('Network Error')
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
        if self.info is (None, None, None):
            message = 'N/A'
        else:
            if kw:
                multiplier = 0.24
                symbol = 'kW'
            else:
                multiplier = 1
                symbol = 'A'
            (currents, estimated, recommended) = self.info
            if currents is None or estimated is None:
                print(currents, estimated, self.info)
                raise TypeError('Unreachable')
            message = []
            for (name, ct, current) in zip(self.config.names, self.config.current_types, currents):
                message.append(f'{round(current * multiplier, rounding)}{symbol}: {name} ({ct.name})')
            if not kw:
                message.append(f'{round(estimated, rounding)}A: Estimated')
                message.append(f'{recommended}A: Recommended')
            message = '\n'.join(message)
        return message

    def update_info(self, currents: list, estimated: float, recommended: int):
        """Update what it knows about the state."""
        self.last_info = self.info
        self.info = (currents, estimated, recommended)
        to_update = set()
        for (i, handlers) in enumerate(self.change_handlers):
            if self.info[i] != self.last_info[i]:
                for handler in handlers:
                    to_update.add(handler)
        for handler in to_update:
            if handler.update() is False:
                self.remove_handler(handler)

    def button(self, update, _):
        """Run the continue button from LiveStatus.update."""
        query = update.callback_query
        query.answer()
        data = query.data.strip().split(' ')
        if len(data) < 2:
            raise TypeError(f'Did not expect {data}')
        else:
            chat_id = int(data[0])
            mes_id = int(data[1])
        self.add_handler(LiveStatusHandler(self, chat_id, 300, mes_id))

    def cleanup(self):
        """Kills all handlers."""
        handlers = set()
        for handler_group in self.change_handlers:
            for handler in handler_group:
                handlers.add(handler)
        for handler in handlers:
            self.remove_handler(handler)
