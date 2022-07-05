"""Datalogs the current readings."""
from config import Config
from current import CurrentMonitor, CurrentType
from datalogger import DataLogger
from pathlib import Path
from tele_bot import TelegramBot


NAMES = ['Solar', 'House', 'Car', 'Heat Pump', 'Grid']
CURRENT_TYPES = [
    CurrentType.Source,
    CurrentType.Drain,
    CurrentType.Unknown,
    CurrentType.Drain,
    CurrentType.Unknown,
]

CONFIG = Config(Path("/home/pi/power_manager"), NAMES, CURRENT_TYPES, 30.7,
                7.5)

if __name__ == '__main__':
    try:
        data_logger = DataLogger(CONFIG, 15, Path('data'))
        tele_bot = TelegramBot(CONFIG, data_logger)
        current_monitor = CurrentMonitor(len(NAMES))

        while True:
            currents = current_monitor.read()
            print(currents)
            data_logger.tick(currents)
            tele_bot.update_current(currents)
    except:  # noqa
        tele_bot.kill()
        CONFIG.logger.exception('Overall:')
        raise
