"""Datalogs the current readings."""
from config import Config
from current import CurrentMonitor, CurrentType
from datalogger import DataLogger
from pathlib import Path
from tele_bot import TelegramBot


NAMES = ['Solar', 'House', 'Car', 'HeatPump', 'Grid']
CURRENT_TYPES = [
    CurrentType.Source,
    CurrentType.Drain,
    CurrentType.Unknown,
    CurrentType.Drain,
    CurrentType.Unknown,
]

CONFIG = Config(Path("/home/pi/power_manager"), NAMES, CURRENT_TYPES)

if __name__ == '__main__':
    tele_bot = TelegramBot(CONFIG)
    data_logger = DataLogger(CONFIG, 15, Path('data'))
    current_monitor = CurrentMonitor(len(NAMES))

    while True:
        currents = current_monitor.read()
        print(currents)
        data_logger.tick(currents)
        tele_bot.update_current(currents)
