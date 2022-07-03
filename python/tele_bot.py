"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from nvi import NonVolatileInformation
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
        self.info = NonVolatileInformation(config.path / 'telegram_info.json')
        self.pause_info = {chat_id: {'enabled': None, 'silent': None}
                           for chat_id in self.info}
        self.updater = Updater(self.info.token)
        self.dispatcher = self.updater.dispatcher
        self._add_command('start', self._start)
        self._add_command('verified', self._verified)
        self.updater.start_polling()

    def _add_command(self, name, func):
        self.dispatcher.add_handler(CommandHandler(name, func))

    def _start(self, update, context):
        if update.message.text == '/start lego':
            self.info.add_chat(update.effective_chat.id)
            self.pause_info[str(update.effective_chat.id)] = \
                {'enabled': None, 'silent': None}
            update.message.reply_text('Password correct')

    @password
    def _verified(self, update, context):
        update.message.reply_text('You are verified')
