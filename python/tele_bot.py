"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from current import Current
from nvi import NonVolatileInformation
from pathlib import Path
from telegram.ext import CommandHandler, Updater


def password(f):
    """Check if this chat has entered the correct password."""
    def wrapper(self, update, context):
        if self.info.is_valid(update.effective_chat.id):
            f(self, update, context)
    return wrapper


class TelegramBot:
    """Control all the aspects of the telegram bot side of it."""

    def __init__(self, config: Config):
        """Set up the necessary functions and operations."""
        self.config = config
        self.info = NonVolatileInformation(config.path /
                                           Path('telegram_info.json'))
        self.updater = Updater(self.info.token)
        self.dispatcher = self.updater.dispatcher
        self._add_command('start', self._start)
        self._add_command('status', self._status)
        self.updater.start_polling()
        self.current = None

    def update_current(self, current: [Current]):
        """Update its known current."""
        self.current = current

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
                message.append(f'{name} ({ct.name}): {round(current, 1)}')
            message = '\n'.join(message)
        update.message.reply_text(message)
