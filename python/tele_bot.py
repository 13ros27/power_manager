"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from current import Current
from datalogger import DataLogger
from nvi import NonVolatileInformation
from pathlib import Path
from telegram.ext import CommandHandler, Updater
import time


def password(f):
    """Check if this chat has entered the correct password."""
    def wrapper(self, update, context):
        if self.info.is_valid(update.effective_chat.id):
            f(self, update, context)
    return wrapper


class TelegramBot:
    """Control all the aspects of the telegram bot side of it."""

    def __init__(self, config: Config, data_logger: DataLogger):
        """Set up the necessary functions and operations."""
        self.config = config
        self.data_logger = data_logger
        self.info = NonVolatileInformation(config.path /
                                           Path('telegram_info.json'))
        self.updater = Updater(self.info.token)
        self.dispatcher = self.updater.dispatcher
        self._add_command('start', self._start)
        self._add_command('status', self._status2)
        self._add_command('latest_file', self._latest_file)
        self._add_command('get_live', self._get_live)
        self.updater.start_polling()
        self.current = None
        self.live = []

    def update_current(self, current: [Current]):
        """Update its known current."""
        self.current = current
        self._update_lives()

    def _update_lives(self):
        for (chat_id, mes_id, live_until) in self.live:
            self.updater.bot.edit_message_text(self._formatted_current(),
                                               chat_id, mes_id)
            if time.time() > live_until:
                self.updater.bot.send_message(chat_id, "Live session ended")
                del self.live[(chat_id, mes_id, live_until)]

    def _add_command(self, name, func):
        self.dispatcher.add_handler(CommandHandler(name, func))

    def _start(self, update, context):
        if update.message.text == '/start lego':
            self.info.add_chat(update.effective_chat.id)
            update.message.reply_text('Password correct')

    @password
    def _status(self, update, context):
        if self.current is None:
            message = 'N/A'
        else:
            message = []
            for (name, ct, current) in zip(self.config.names,
                                           self.config.current_types,
                                           self.current):
                message.append(
                    f'{name} ({ct.name}): {round(current.amps, 1)}A')
            message = '\n'.join(message)
        update.message.reply_text(message)

    def _formatted_current(self):
        if self.current is None:
            message = 'N/A'
        else:
            message = '<pre>'
            for (name, ct, current) in zip(self.config.names,
                                           self.config.current_types,
                                           self.current):
                message += f'{name} ({ct.name}):'.ljust(18)
                message += f'{round(current.amps, 1)}A\n'
            message += '</pre>'
        return message

    @password
    def _status2(self, update, context):
        update.message.reply_html(self._formatted_current())

    @password
    def _latest_file(self, update, context):
        update.message.reply_document(open(self.data_logger.fp, 'rb'))

    @password
    def _get_live(self, update, context):
        sp = update.message.text.split(' ')
        if len(sp) >= 1:
            live_until = time.time() + sp[1]
        else:
            live_until = time.time() + 300
        mes = update.message.reply_text(self._formatted_current())
        self.live.append((update.effective_chat.id, mes.message_id,
                          live_until))
