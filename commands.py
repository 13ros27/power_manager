from pathlib import Path
from config import Config
from datalogger import DataLogger
from handlers import LiveStatusHandler, RecommendHandler
from state import Mode, Modes
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
        tbot = TelegramBot(config, Modes(config, Mode.OFF, quasar))
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
        tbot.add_command('charger_status', self.charger_status)
        tbot.add_command('soc', self.soc)
        tbot.add_command('test', self.test)
        tbot.add_command('off', self.off)
        tbot.add_command('manual', self.manual)
        tbot.add_command('auto', self.auto)
        tbot.add_command('charge_only', self.charge_only)
        tbot.add_command('charge_discharge', self.charge_discharge)
        tbot.add_command('ccl', self.charge_cost_limit)
        tbot.add_command('sdv', self.stored_discharge_value)
        tbot.add_command('mdr', self.min_discharge_rate)
        tbot.add_command('disconnect', self.min_discharge_rate)

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
    def test(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, f'RPi thinks {self.quasar._charging}, Quasar thinks {self.quasar.read_register(0x101)}.')

    @password
    def off(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(Mode.OFF)
        self.tbot.reply_text(update, 'Set user mode to OFF')

    @password
    def manual(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(self.tbot.charge_mode)
        self.tbot.reply_text(update, f'Set user mode to {self.tbot.charge_mode.name}')

    @password
    def auto(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(Mode.AUTO)
        self.tbot.reply_text(update, 'Set user mode to AUTO')

    @password
    def charge_only(self, update: Update, _: CallbackContext):
        self.tbot.charge_mode = Mode.CHARGE_ONLY
        if self.tbot.modes._mode == Mode.CHARGE_DISCHARGE:
            self.tbot.modes.set_mode(self.tbot.charge_mode)
        self.tbot.reply_text(update, 'Set charge mode to CHARGE_ONLY')

    @password
    def charge_discharge(self, update: Update, _: CallbackContext):
        self.tbot.charge_mode = Mode.CHARGE_DISCHARGE
        if self.tbot.modes._mode == Mode.CHARGE_ONLY:
            self.tbot.modes.set_mode(self.tbot.charge_mode)
        self.tbot.reply_text(update, 'Set charge mode to CHARGE_DISCHARGE')

    @password
    def charge_cost_limit(self, update: Update, _: CallbackContext):
        mes = f'The charge cost limit is {round(self.tbot.modes.user_settings.charge_cost_limit, 1)}p'
        mes_id = self.tbot.reply_text(update, mes).message_id
        chat_id = self.tbot.get_chat_id(update)
        inbuilt_vals = {'Free': 0.0, 'Below Off Peak': self.config.low_night, 'Off Peak': self.config.high_night,
                        'Below Peak': self.config.low_day, 'Peak': self.config.high_day}
        buttons = []
        for (name, val) in inbuilt_vals.items():
            button = InlineKeyboardButton(name, callback_data=f'{chat_id} {mes_id} 0 {val}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id, reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def stored_discharge_value(self, update: Update, _: CallbackContext):
        mes = f'The stored discharge value is {round(self.tbot.modes.user_settings.stored_discharge_value, 1)}p'
        mes_id = self.tbot.reply_text(update, mes).message_id
        chat_id = self.tbot.get_chat_id(update)
        inbuilt_vals = {'Free': 0.0, 'Off Peak': self.config.discharge_rate, 'Peak': self.config.low_day}
        buttons = []
        for (name, val) in inbuilt_vals.items():
            button = InlineKeyboardButton(name, callback_data=f'{chat_id} {mes_id} 1 {val}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id, reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def min_discharge_rate(self, update: Update, _: CallbackContext):
        mdr = self.tbot.second_item(update, error='Incorrectly formatted command, please specify a min discharge rate')
        self.tbot.modes.user_settings.min_discharge_rate = int(mdr)
        self.tbot.reply_text(update, f'Set the min discharge rate to {int(mdr)}A')

    @password
    def disconnect(self, update: Update, _: CallbackContext):
        self.quasar.disconnect()
        self.tbot.reply_text(update, 'Disconnected for 30 seconds')

    def cleanup(self):
        self.tbot.cleanup()
