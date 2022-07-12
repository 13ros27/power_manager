from commands import TeleCommands
from config import Config
from current import CurrentMonitor, CurrentType, current_combine
from datalogger import DataLogger
from pathlib import Path
from quasar import Quasar
from recommend import Recommend


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
    CONFIG = Config(Path("/home/pi/power_manager"), NAMES, CURRENT_TYPES, 30.7, 7.5, 13.0, (0, 30), (4, 30))
    commands = None
    quasar = None
    try:
        data_logger = DataLogger(CONFIG, 15, Path('data'))
        quasar = Quasar(QUASAR_ADDR)
        commands = TeleCommands(CONFIG, data_logger, quasar)
        current_monitor = CurrentMonitor(len(NAMES))
        recommend = Recommend(CONFIG)

        while True:
            currents = current_monitor.read()
            print(currents)
            data_logger.tick(currents)
            estimated = current_combine(currents, CURRENT_TYPES)
            recommended = recommend.current(estimated)
            commands.tbot.update_info(currents, estimated, recommended)
            if commands.tbot.following:
                quasar.set_charge_rate(recommended)
    except:  # noqa
        CONFIG.logger.exception('Overall:')
        raise
    finally:
        if commands is not None:
            commands.cleanup()
        if quasar is not None:
            quasar.cleanup()
