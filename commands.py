from pathlib import Path
from config import Config
from datalogger import DataLogger
from handlers import LiveStatusHandler, RecommendHandler
from tele_bot import TelegramBot
from telegram import Update
from telegram.ext import CallbackContext
from quasar import Quasar

def password(f):
    """Check if this chat has entered the correct password."""
    def wrapper(self, update: Update, context: CallbackContext):
        if self.tbot.nvinfo.is_valid(self.tbot.get_chat_id(update)):
            f(self, update, context)
    return wrapper

class TeleCommands:
    def __init__(self, config: Config, datalogger: DataLogger, quasar: Quasar):
        self.config = config
        self.datalogger = datalogger
        self.quasar = quasar
        self.following = False
        tbot = TelegramBot(config)
        self.tbot = tbot
        self.recommending = {}
        tbot.add_command('start', self.start)
        tbot.add_command('status', self.status)
        tbot.add_command('latestfile', self.latestfile)
        tbot.add_command('live', self.live)
        tbot.add_command('log', self.log)
        tbot.add_command('listfiles', self.listfiles)
        tbot.add_command('file', self.file)
        tbot.add_command('statuskw', self.statuskw)
        tbot.add_command('recommend', self.recommend)
        tbot.add_command('follow', self.follow)
        tbot.add_command('charger_status', self.charger_status)

    def start(self, update: Update, _: CallbackContext):
        if update.message.text == '/start lego':
            if self.tbot.add_chat(update):
                self.tbot.reply_text(update, 'Password correct')

    @password
    def status(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, self.tbot.formatted_current())

    @password
    def latestfile(self, update: Update, _: CallbackContext):
        self.tbot.reply_document(update, self.datalogger.fp)

    @password
    def live(self, update: Update, _: CallbackContext):
        secs_for = int(self.tbot.second_item(update, default=5))*60
        self.tbot.add_handler(LiveStatusHandler(self.tbot, self.tbot.get_chat_id(update), secs_for))

    @password
    def log(self, update: Update, _: CallbackContext):
        sp = update.message.text[5:].strip()
        if len(sp) > 0:
            self.datalogger.add_metadata(sp)
            self.tbot.reply_text(update, f'Added \'{sp}\' to the log')
        else:
            self.tbot.reply_text(update, 'Incorrectly formatted command, please specify something to log')

    @password
    def listfiles(self, update: Update, _: CallbackContext):
        files = [f.stem for f in self.datalogger.folder.iterdir()]
        files.sort()
        self.tbot.reply_text(update, ', '.join(files))

    @password
    def file(self, update: Update, _: CallbackContext):
        file = self.tbot.second_item(update, error='Incorrectly formatted command, please specify a file')
        if file != '':
            file = self.datalogger.folder / Path(f'{file}.csv')
            if not file.exists():
                self.tbot.reply_text(update, f'File: {file} does not exist')
            else:
                self.tbot.reply_document(update, file)

    @password
    def statuskw(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, self.tbot.formatted_current(rounding = 2, kw = True))

    @password
    def recommend(self, update: Update, _: CallbackContext):
        chat_id = self.tbot.get_chat_id(update)
        recommending = self.recommending.get(chat_id)
        is_live = False
        if recommending is not None:
            is_live = not recommending.is_finished()
        mins_for = self.tbot.second_item(update, default='')
        if mins_for == '':
            if is_live:
                self.tbot.reply_text(update, 'Toggled recommendations off')
                self.tbot.remove_handler(recommending)
            else:
                self.tbot.reply_text(update, 'Toggled recommendations on')
                handler = RecommendHandler(self.tbot, chat_id)
                self.tbot.add_handler(handler)
                self.recommending[chat_id] = handler
        else:
            secs_for = int(mins_for)*60
            if recommending is not None:
                recommending.update_timer(secs_for)
            else:
                handler = RecommendHandler(self.tbot, chat_id, secs_for)
                self.tbot.add_handler(handler)
                self.recommending[chat_id] = handler

    @password
    def follow(self, update: Update, _: CallbackContext):
        if self.following:
            self.quasar.relinquish_control()
            self.tbot.reply_text(update, 'Toggled following off')
        else:
            self.quasar.take_control()
            self.tbot.reply_text(update, 'Toggled following on')
        self.following = not self.following

    @password
    def charger_status(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, self.quasar.read_charger_status().name)

    def cleanup(self):
        self.tbot.cleanup()
