"""Datalogs the current readings."""
from config import Config
from current import CurrentMonitor, CurrentType, current_combine, recommended_current
from datalogger import DataLogger
from pathlib import Path
from commands import TeleCommands
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
    commands = None
    quasar = None
    try:
        data_logger = DataLogger(CONFIG, 15, Path('data'))
        quasar = Quasar(QUASAR_ADDR, take_control=False)
        commands = TeleCommands(CONFIG, data_logger, quasar)
        current_monitor = CurrentMonitor(len(NAMES))

        while True:
            currents = current_monitor.read()
            print(currents)
            data_logger.tick(currents)
            estimated = current_combine(currents, CURRENT_TYPES)
            recommended = recommended_current(CONFIG, estimated)
            commands.tbot.update_info(currents, estimated, recommended)
    except:  # noqa
        CONFIG.logger.exception('Overall:')
        raise
    finally:
        if commands is not None:
            commands.cleanup()
        if quasar is not None:
            quasar.cleanup()
