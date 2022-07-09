"""Datalogs the current readings."""
from config import Config
from current import CurrentMonitor, CurrentType
from datalogger import DataLogger
from pathlib import Path
from tele_bot import TelegramBot
from quasar import Quasar


NAMES = ['Solar', 'House', 'Car', 'Heat Pump', 'Grid']
CURRENT_TYPES = [
    CurrentType.Source,
    CurrentType.Drain,
    CurrentType.Unknown,
    CurrentType.Drain,
    CurrentType.Unknown,
]
QUASAR_ADDR = '192.168.1.74'

if __name__ == '__main__':
    CONFIG = Config(Path("/home/pi/power_manager"), NAMES, CURRENT_TYPES, 30.7, 7.5)
    tele_bot = None
    try:
        data_logger = DataLogger(CONFIG, 15, Path('data'))
        quasar = Quasar(QUASAR_ADDR)
        tele_bot = TelegramBot(CONFIG, data_logger, quasar)
        current_monitor = CurrentMonitor(len(NAMES))

        while True:
            currents = current_monitor.read()
            print(currents)
            data_logger.tick(currents)
            tele_bot.update_current(currents)
    except:  # noqa
        CONFIG.logger.exception('Overall:')
        raise
    finally:
        if tele_bot is not None:
            tele_bot.cleanup()
