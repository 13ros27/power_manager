from pathlib import Path
from config import Config
from datalogger import DataLogger
from handlers import LiveStatusHandler, RecommendHandler
from state import StateSelect, Mode
from tele_bot import TelegramBot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
        self.state_select = StateSelect(Mode.PRESERVE, config, quasar)
        self.following = False
        tbot = TelegramBot(config, self.state_select)
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
        tbot.add_command('following', self.isfollowing)
        tbot.add_command('charger_status', self.charger_status)
        tbot.add_command('soc', self.soc)
        tbot.add_command('mode', self.mode)
        tbot.add_command('test', self.test)

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
                self.recommending[chat_id] = None
            else:
                self.tbot.reply_text(update, 'Toggled recommendations on')
                handler = RecommendHandler(self.tbot, chat_id)
                self.tbot.add_handler(handler)
                self.recommending[chat_id] = handler
        else:
            secs_for = int(mins_for)*60
            if recommending is not None:
                self.tbot.reply_text(update, f'Extending recommendations for {mins_for} minutes')
                recommending.update_timer(secs_for)
            else:
                self.tbot.reply_text(update, f'Toggling recommendations on for {mins_for} minutes')
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
    def isfollowing(self, update: Update, _: CallbackContext):
        if self.following:
            self.tbot.reply_text(update, 'I am following')
        else:
            self.tbot.reply_text(update, 'I am not following')

    @password
    def charger_status(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, self.quasar.charger_status.name)

    @password
    def soc(self, update: Update, _: CallbackContext):
        soc = self.quasar.soc
        if soc == 0:
            self.tbot.reply_text(update, f'Unknown')
        else:
            self.tbot.reply_text(update, f'{soc}%')

    @password
    def mode(self, update: Update, _: CallbackContext):
        chat_id = self.tbot.get_chat_id(update)
        message = f'Current mode is {self.state_select.mode.name}'
        mes = self.tbot.reply_text(update, message)
        if mes is not None:
            buttons = []
            for mode in Mode:
                button = InlineKeyboardButton(mode.name, callback_data=f'{chat_id} {mes.message_id} {mode.value}')
                if buttons == [] or len(buttons[-1]) != 1:
                    buttons.append([button])
                else:
                    buttons[-1].append(button)
            self.tbot.edit_message_text(message, chat_id, mes.message_id, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            self.config.logger.warning('/mode found no mes_id')

    @password
    def test(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, f'RPi thinks {self.quasar._charging}, Quasar thinks {self.quasar.read_register(0x101)}.')

    def cleanup(self):
        self.tbot.cleanup()
