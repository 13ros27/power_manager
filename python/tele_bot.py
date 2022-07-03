"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from current import Current, current_combine
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
        self._add_command('status', self._status)
        self._add_command('latest_file', self._latest_file)
        self._add_command('get_live', self._get_live)
        self._add_command('log', self._log)
        self.updater.start_polling()
        self.current = None
        self.live = []
        self.last_message = None

    def update_current(self, current: [Current]):
        """Update its known current."""
        self.last_message = self._formatted_current()
        self.current = current
        self._update_lives()

    def _update_lives(self):
        formatted = self._formatted_current()
        if formatted != self.last_message:
            to_remove = []
            for (i, (chat_id, mes_id, live_until)) in enumerate(self.live):            
                self.updater.bot.edit_message_text(self._formatted_current(),
                                                   chat_id, mes_id)
                if time.time() > live_until:
                    self.updater.bot.send_message(chat_id,
                                                  "Live session ended")
                    to_remove.append(i)
            for index in to_remove:
                del self.live[index]

    def _add_command(self, name, func):
        self.dispatcher.add_handler(CommandHandler(name, func))

    def _start(self, update, context):
        if update.message.text == '/start lego':
            self.info.add_chat(update.effective_chat.id)
            update.message.reply_text('Password correct')

    def _formatted_current(self):
        if self.current is None:
            message = 'N/A'
        else:
            message = []
            for (name, ct, current) in zip(self.config.names,
                                           self.config.current_types,
                                           self.current):
                message.append(f'{round(current.amps,1)}A: {name} ({ct.name})')
            estimated = current_combine(self.current,
                                        self.config.current_types)
            message.append(f'{round(estimated, 1)}A: Estimated')
            message = '\n'.join(message)
        return message

    @password
    def _status(self, update, context):
        update.message.reply_text(f'{self._formatted_current()}')

    @password
    def _latest_file(self, update, context):
        update.message.reply_document(open(self.data_logger.fp, 'rb'))

    @password
    def _get_live(self, update, context):
        sp = update.message.text.split(' ')
        if len(sp) >= 2:
            live_until = time.time() + int(sp[1])
        else:
            live_until = time.time() + 300
        mes = update.message.reply_text(self._formatted_current())
        self.live.append((update.effective_chat.id, mes.message_id,
                          live_until))

    @password
    def _log(self, update, context):
        sp = update.message.text.split(' ')
        if len(sp) >= 2:
            self.data_logger.add_metadata(sp[1])
            update.message.reply_text(f'Added \'{sp[1]}\' to the log')
        else:
            update.message.reply_text('Incorrectly formatted command, please \
                                       specify something to log')
