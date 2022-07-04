"""Contains the class that handles anything to do with the telegram bot."""
from config import Config
from current import current_combine, recommended_current
from datalogger import DataLogger
from nvi import NonVolatileInformation
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, Updater
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
        self._add_command('latestfile', self._latest_file)
        self._add_command('live', self._live)
        self._add_command('log', self._log)
        self._add_command('listfiles', self._list_files)
        self._add_command('file', self._file)
        self._add_command('statuskw', self._statuskw)
        self._add_command('kill', self._kill)
        self.dispatcher.add_handler(CallbackQueryHandler(self.button))
        self.updater.start_polling()
        self.current = None
        self.live = []
        self.last_message = None
        self.last_recommendations = {}
        self.recommended = '0'

    def _add_command(self, name, func):
        self.dispatcher.add_handler(CommandHandler(name, func))

    def update_current(self, current: [float]):
        """Update its known current."""
        self.last_message = self._formatted_current()
        self.current = current
        self._update_lives()

    def _send(self, command, *args, **kwargs):
        try:
            self.logger.info(f'{command}({", ".join(map(str, args))}, \
{kwargs})')
            return command(*args, **kwargs)
        except:  # noqa
            self.logger.exception('Telegram Bot:')

    def reply_text(self, update, text: str):
        """Reply with a text message, with error handling."""
        return self._send(update.message.reply_text, text)

    def reply_document(self, update, filepath: Path):
        """Reply with a document from a particular filepath."""
        return self._send(update.message.reply_document, open(filepath, 'rb'))

    def send_text(self, text: str, chat_id, silent=False, **kwargs):
        """Send a text message to a given chat."""
        return self._send(self.updater.bot.send_message, chat_id, text,
                          disable_notification=silent, **kwargs)

    def edit_message_text(self, text: str, chat_id, mes_id, **kwargs):
        """Edit a given message."""
        return self._send(self.updater.bot.edit_message_text, text, chat_id,
                          mes_id, **kwargs)

    def _update_lives(self):
        formatted = self._formatted_current()
        if formatted != self.last_message:
            to_remove = []
            for (i, (chat_id, mes_id, live_until)) in enumerate(self.live):
                if time.time() > live_until:
                    message = formatted
                    markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton('Continue', callback_data=f'\
                                             {chat_id} {mes_id}')]])
                    to_remove.append(i)
                else:
                    message = f'LIVE\n{formatted}'
                    markup = None
                self.edit_message_text(message, chat_id, mes_id,
                                       reply_markup=markup)
            for index in to_remove[::-1]:
                del self.live[index]

    def button(self, update, context):
        """Run the continue button from _update_lives."""
        query = update.callback_query
        query.answer()
        data = query.data.strip().split(' ')
        if len(data) < 2:
            raise TypeError(f'Did not expect {data}')
        else:
            chat_id = int(data[0])
            mes_id = int(data[1])
        self._go_live(chat_id, mes_id=mes_id)

    def _update_recommended(self):
        for chat_id in enumerate(self.nvi):
            recommended = self.nvi[chat_id]['recommend']
            send = recommended is True
            if isinstance(recommended, float):
                if time.time() > recommended:
                    self.nvi.setitem(chat_id, 'recommend', False)
                    self.last_recommendations[chat_id] = None
                else:
                    send = True
            if send:
                last = self.last_recommendations.get(chat_id)
                mes = self.send_text(f'Recommendation: {self.recommended}A')
                self.last_recommendations[chat_id] = mes.message_id
                if last is not None:
                    self.updater.bot.delete_message(chat_id, last)

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
                message.append(f'{round(current, 1)}A: {name} ({ct.name})')
            estimated = current_combine(self.current,
                                        self.config.current_types)
            message.append(f'{round(estimated, 1)}A: Estimated')
            old_recommended = self.recommended
            self.recommended = recommended_current(self.config, estimated)
            if self.recommended > 0:
                self.recommended = f'+{self.recommended}'
            if old_recommended != self.recommended:
                self._update_recommended()
            message.append(f'{self.recommended}A: Recommended')
            message = '\n'.join(message)
        return message

    def _go_live(self, chat_id, secs_for=300, mes_id=None):
        live_until = time.time() + secs_for
        text = f'LIVE\n{self._formatted_current()}'
        if mes_id is None:
            mes = self.send_text(text, chat_id)
            mes_id = mes.message_id
        else:
            self.edit_message_text(text, chat_id, mes_id)
        self.live.append((chat_id, mes_id, live_until))

    @password
    def _status(self, update, context):
        self.reply_text(update, self._formatted_current())

    @password
    def _latest_file(self, update, context):
        self.reply_document(update, self.data_logger.fp)

    @password
    def _live(self, update, context):
        sp = update.message.text.split(' ')
        secs_for = 300
        if len(sp) >= 2:
            secs_for = int(sp[1])*60
        self._go_live(update.effective_chat.id, secs_for)

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
        files.sort()
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

    @password
    def _statuskw(self, update, context):
        if self.current is None:
            message = 'N/A'
        else:
            message = []
            for (name, ct, current) in zip(self.config.names,
                                           self.config.current_types,
                                           self.current):
                message.append(f'{round(current*0.24, 2)}kW: {name} \
({ct.name})')
        self.reply_text(update, '\n'.join(message))

    @password
    def _recommend(self, update, context):
        chat_id = update.effective_chat.id
        sp = update.message.text.split(' ')
        if len(sp) == 1:
            toggle = True
        else:
            toggle = False
        if toggle:
            if self.nvi[chat_id]['recommend'] is False:
                self.reply_text(update, 'Toggled recommend on')
                self.nvi.setitem(chat_id, 'recommend', True)
            else:
                self.reply_text(update, 'Toggled recommend off')
                self.nvi.setitem(chat_id, 'recommend', False)
        else:
            self.reply_text(update, 'Toggled recommend on for {sp[1]} minutes')
            self.nvi.setitem(chat_id, 'recommend', time.time() + sp[1]*60)

    @password
    def _kill(self, update, context):
        self.kill()

    def kill(self):
        """Kills all live messages."""
        chats = set()
        for (chat_id, mes_id, live_until) in self.live:
            chats.add(chat_id)
            self.edit_message_text(self._formatted_current(), chat_id, mes_id)
        self.live = []
        for chat in chats:
            self.send_text("Going offline", chat, silent=True)
