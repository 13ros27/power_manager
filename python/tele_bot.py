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
        self.logger = config.logger
        self.data_logger = data_logger
        self.info = NonVolatileInformation(config.path /
                                           Path('telegram_info.json'))
        self.updater = Updater(self.info.token)
        self.dispatcher = self.updater.dispatcher
        self._add_command('start', self._start)
        self._add_command('status', self._status)
        self._add_command('latest_file', self._latest_file)
        self._add_command('live', self._live)
        self._add_command('log', self._log)
        self._add_command('listfiles', self._list_files)
        self._add_command('file', self._file)
        self.updater.start_polling()
        self.current = None
        self.live = []
        self.last_message = None

    def update_current(self, current: [Current]):
        """Update its known current."""
        self.last_message = self._formatted_current()
        self.current = current
        self._update_lives()

    def _send(self, command, *args, **kwargs):
        try:
            self.logger.info(f'{command}({", ".join(args)}, {kwargs})')
            return command(*args, **kwargs)
        except:  # noqa
            self.logger.exception('Telegram Bot: ')

    def reply_text(self, update, text: str):
        """Reply with a text message, with error handling."""
        return self._send(update.message.reply_text, text)

    def reply_document(self, update, filepath: Path):
        """Reply with a document from a particular filepath."""
        return self._send(update.message.reply_document, open(filepath, 'rb'))

    def send_text(self, text: str, chat_id, silent=False):
        """Send a text message to a given chat."""
        return self._send(self.updater.bot.send_message, chat_id, text,
                          disable_notification=silent)

    def edit_message_text(self, text: str, chat_id, mes_id):
        """Edit a given message."""
        return self._send(self.updater.bot.edit_message_text, text, chat_id,
                          mes_id)

    def _update_lives(self):
        formatted = self._formatted_current()
        if formatted != self.last_message:
            to_remove = []
            for (i, (chat_id, mes_id, live_until)) in enumerate(self.live):
                if time.time() > live_until:
                    message = f'{formatted}'
                else:
                    message = f'LIVE\n{formatted}'
                self.edit_message_text(message, chat_id, mes_id)
                if time.time() > live_until:
                    self.send_text("Live session ended", chat_id, silent=True)
                    to_remove.append(i)
            for index in to_remove[::-1]:
                del self.live[index]

    def _add_command(self, name, func):
        self.dispatcher.add_handler(CommandHandler(name, func))

    def _start(self, update, context):
        if update.message.text == '/start lego':
            self.info.add_chat(update.effective_chat.id)
            self.reply_text(update, 'Password correct')

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
        self.reply_text(update, f'{self._formatted_current()}')

    @password
    def _latest_file(self, update, context):
        self.reply_document(update, self.data_logger.fp)

    @password
    def _live(self, update, context):
        sp = update.message.text.split(' ')
        if len(sp) >= 2:
            live_until = time.time() + int(sp[1])*60
        else:
            live_until = time.time() + 300
        mes = self.reply_text(update, f'LIVE\n{self._formatted_current()}')
        self.live.append((update.effective_chat.id, mes.message_id,
                          live_until))

    @password
    def _log(self, update, context):
        sp = update.message.text[5:]
        if len(sp) > 0:
            self.data_logger.add_metadata(sp)
            self.reply_text(update, f'Added \'{sp}\' to the log')
        else:
            self.reply_text(update, 'Incorrectly formatted command, please \
specify something to log')

    @password
    def _list_files(self, update, context):
        files = [f.stem for f in self.data_logger.folder.iterdir()]
        self.reply_text(update, ', '.join(files))

    @password
    def _file(self, update, context):
        sp = update.message.text.split(' ')
        if len(sp) == 1:
            self.reply_text(update, 'Incorrectly formatted command, please \
specify a file')
        else:
            file = self.data_logger.folder / Path(f'{sp[1]}.csv')
            if not file.exists():
                self.reply_text(update, f'File: {file} does not exist')
            else:
                self.reply_document(update, file)
