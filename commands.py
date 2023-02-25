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
        tbot = TelegramBot(config, datalogger, Mode.OFF, quasar)
        self.tbot = tbot
        self.pump_threshold = 99.0
        self.pump_subtractor = 0.0
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
        tbot.add_command('auto', self.auto)
        tbot.add_command('user_mode', self.user_mode)
        tbot.add_command('manual', self.manual)
        tbot.add_command('charge_only', self.charge_only)
        tbot.add_command('charge_discharge', self.charge_discharge)
        tbot.add_command('max_charge', self.max_charge)
        tbot.add_command('charge_cost_limit', self.charge_cost_limit)
        tbot.add_command('discharge_value', self.discharge_value)
        tbot.add_command('min_discharge_rate', self.min_discharge_rate)
        tbot.add_command('disconnect', self.disconnect)
        tbot.add_command('max_paid_soc', self.max_paid_soc)
        tbot.add_command('min_discharge_soc', self.min_discharge_soc)
        tbot.add_command('settings', self.settings)
        tbot.add_command('pump_threshold', self.change_pump_threshold)
        tbot.add_command('pump_subtractor', self.change_pump_subtractor)
        tbot.add_command('more', self.more)
        tbot.add_command('kill', self.kill)

    def start(self, update: Update, _: CallbackContext):
        if update.message.text == '/start lego':
            if self.tbot.add_chat(update):
                self.tbot.reply_text(update, 'Password correct')

    def notify(self, update: Update, text: str):
        self.tbot.reply_text(update, text)
        self.datalogger.add_metadata(text)

    @password
    def status(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, self.tbot.formatted_current())

    @password
    def latestfile(self, update: Update, _: CallbackContext):
        self.tbot.reply_document(update, self.datalogger.fp)

    @password
    def live(self, update: Update, _: CallbackContext):
        secs_for = int(self.tbot.second_item(update, default=5))*60
        self.tbot.add_handler(LiveStatusHandler(self.tbot, self.tbot.get_chat_id(update),
                                                secs_for))

    @password
    def log(self, update: Update, _: CallbackContext):
        sp = update.message.text[5:].strip()
        if len(sp) > 0:
            self.datalogger.add_metadata(sp)
            self.tbot.reply_text(update, f'Added \'{sp}\' to the log')
        else:
            self.tbot.reply_text(update, 'Please enter something to log:')
            self.tbot.particular_message_handler = (self._log, update.effective_chat.id)

    def _log(self, message) -> tuple:
        self.datalogger.add_metadata(message)
        self.tbot.particular_message_handler = None
        return (f'Added \'{message}\' to the log', False)

    @password
    def listfiles(self, update: Update, _: CallbackContext):
        files = [f.stem for f in self.datalogger.folder.iterdir()]
        files.sort()
        self.tbot.reply_text(update, ', '.join(files))

    @password
    def file(self, update: Update, _: CallbackContext):
        file = self.tbot.second_item(update,
                                     error='Incorrectly formatted command, please specify a file')
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
        self.notify(update, 'Set user mode to OFF')

    @password
    def auto(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(Mode.AUTO)
        self.notify(update, 'Set user mode to AUTO')

    @password
    def manual(self, update: Update, _: CallbackContext):
        mes = f'The user mode is currently {self.tbot.modes._mode.name}'
        mes_id = self.tbot.reply_text(update, mes)
        chat_id = self.tbot.get_chat_id(update)
        modes = [Mode.CHARGE_ONLY, Mode.CHARGE_DISCHARGE, Mode.MAX_CHARGE]
        buttons = []
        for mode in modes:
            button = InlineKeyboardButton(mode.name,
                                          callback_data=f'{chat_id} {mes_id} 2 {mode.value}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id,
                                    reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def user_mode(self, update: Update, _: CallbackContext):
        mes = f'The user mode is currently {self.tbot.modes._mode.name}'
        mes_id = self.tbot.reply_text(update, mes)
        chat_id = self.tbot.get_chat_id(update)
        buttons = []
        for mode in Mode:
            button = InlineKeyboardButton(mode.name,
                                          callback_data=f'{chat_id} {mes_id} 2 {mode.value}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id,
                                    reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def charge_only(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(Mode.CHARGE_ONLY)
        self.notify(update, 'Set user mode to CHARGE_ONLY')

    @password
    def charge_discharge(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(Mode.CHARGE_DISCHARGE)
        self.notify(update, 'Set user mode to CHARGE_DISCHARGE')

    @password
    def max_charge(self, update: Update, _: CallbackContext):
        self.tbot.modes.set_mode(Mode.MAX_CHARGE)
        self.notify(update, 'Set user mode to MAX_CHARGE')

    @password
    def charge_cost_limit(self, update: Update, _: CallbackContext):
        mes = f'The charge cost limit is \
{round(self.tbot.modes.user_settings.charge_cost_limit, 1)}p'
        mes_id = self.tbot.reply_text(update, mes)
        chat_id = self.tbot.get_chat_id(update)
        buttons = []
        for (name, val) in self.tbot.charge_vals:
            button = InlineKeyboardButton(name, callback_data=f'{chat_id} {mes_id} 0 {val}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id,
                                    reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def discharge_value(self, update: Update, _: CallbackContext):
        us = self.tbot.modes.user_settings
        if us.discharge_value != us.low_discharge_value:
            dis_text = f'{round(us.discharge_value, 1)}p [{round(us.low_discharge_value, 1)}p]'
        else:
            dis_text = f'{round(us.discharge_value, 1)}p'
        mes = f'The discharge value is {dis_text}'
        mes_id = self.tbot.reply_text(update, mes)
        chat_id = self.tbot.get_chat_id(update)
        buttons = []
        for (name, val) in self.tbot.discharge_vals:
            proc_val = '_'.join([str(n) for n in val])
            button = InlineKeyboardButton(name, callback_data=f'{chat_id} {mes_id} 1 {proc_val}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id,
                                    reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def min_discharge_rate(self, update: Update, _: CallbackContext):
        mdr = self.tbot.second_item(update, error='Incorrectly formatted command, please specify a min discharge rate')
        self.tbot.modes.user_settings.min_discharge_rate = int(mdr)
        self.notify(update, f'Set the min discharge rate to {int(mdr)}A')

    @password
    def disconnect(self, update: Update, _: CallbackContext):
        secs = self.tbot.second_item(update, default=30)
        self.quasar.disconnect(int(secs))
        self.notify(update, f'Disconnected for {secs} seconds')

    @password
    def max_paid_soc(self, update: Update, _: CallbackContext):
        mes = f'The max paid SoC is {int(self.tbot.modes.user_settings.max_paid_soc)}%, the current SoC is {self.quasar.soc}%'
        mes_id = self.tbot.reply_text(update, mes)
        chat_id = self.tbot.get_chat_id(update)
        possibles = [80, 85, 90, 95, -1]
        buttons = []
        for val in possibles:
            button = InlineKeyboardButton(f'{val}%' if val != -1 else 'Custom',
                                          callback_data=f'{chat_id} {mes_id} 3 {val}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id,
                                    reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def min_discharge_soc(self, update: Update, _: CallbackContext):
        mes = f'The min discharge SoC is {int(self.tbot.modes.user_settings.min_discharge_soc)}%, the current SoC is {self.quasar.soc}%'
        mes_id = self.tbot.reply_text(update, mes)
        chat_id = self.tbot.get_chat_id(update)
        possibles = [30, 40, 50, -1]
        buttons = []
        for val in possibles:
            button = InlineKeyboardButton(f'{val}%' if val != -1 else 'Custom',
                                          callback_data=f'{chat_id} {mes_id} 4 {val}')
            if buttons == [] or len(buttons[-1]) != 1:
                buttons.append([button])
            else:
                buttons[-1].append(button)
        self.tbot.edit_message_text(mes, chat_id, mes_id,
                                    reply_markup=InlineKeyboardMarkup(buttons))

    @password
    def settings(self, update: Update, _: CallbackContext):
        mes_id = self.tbot.reply_text(update, self.tbot.settings_text())
        self.tbot.last_settings[self.tbot.get_chat_id(update)] = mes_id

    @password
    def change_pump_threshold(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, f'The pump threshold is currently {self.tbot.nvinfo.get_general('pump_threshold')}, please enter a new value:')
        self.tbot.particular_message_handler = (self._change_pump_threshold, update.effective_chat.id)

    def _change_pump_threshold(self, message) -> tuple:
        self.tbot.particular_message_handler = None
        try:
            self.tbot.nvinfo.set_general('pump_threshold', float(message))
            return (f'Changed the pump threshold to \'{message}\'', False)
        except ValueError:
            return ('Failed to change pump threshold', False)

    @password
    def change_pump_subtractor(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, f'The pump subtractor is currently {self.tbot.nvinfo.get_general('pump_subtractor')}, please enter a new value:')
        self.tbot.particular_message_handler = (self._change_pump_subtractor, update.effective_chat.id)

    def _change_pump_subtractor(self, message) -> tuple:
        self.tbot.particular_message_handler = None
        try:
            self.tbot.nvinfo.set_general(float(message))
            return (f'Changed the pump subtractor to \'{message}\'', False)
        except ValueError:
            return ('Failed to change pump subtractor', False)

    @password
    def more(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, '''/log - Add something to the datalog
/statuskw - Status in kW
/latestfile - Download latest datalog file
/listfiles - List all datalog files
/file <filename> - Download a given datalog file
/recommend - Ping with any recommendation changes
/charger_status - Get the current charger status
/soc - Get the state of charge of the car
/test - (temp) Testing the morning behaviour
/min_discharge_rate - Set the minimum discharge rate
/pump_threshold - Change the heat pump subtraction threshold
/pump_subtractor - Change how much the heat pump subtracts when above its threshold
/kill - Shut down the program
/more - Self-referential = fun''')

    @password
    def kill(self, update: Update, _: CallbackContext):
        self.tbot.reply_text(update, 'Shutting down the program')
        raise KeyboardInterrupt

    def cleanup(self):
        self.tbot.cleanup()
