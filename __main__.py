from commands import TeleCommands
from config import Config
from current import CurrentMonitor, CurrentType, current_combine
from datalogger import DataLogger
from hysteresis import OnOff
from pathlib import Path
from quasar import Quasar
from recommend import Recommend
from state import Mode

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
    CONFIG = Config(Path("/home/pi/power_manager"), NAMES, CURRENT_TYPES, 30.7, 7.5, 0.8, (0, 30), (4, 30), 40, 80, 90)
    commands = None
    quasar = None
    try:
        data_logger = DataLogger(CONFIG, 15, Path('data'))
        quasar = Quasar(QUASAR_ADDR)
        commands = TeleCommands(CONFIG, data_logger, quasar)
        current_monitor = CurrentMonitor(len(NAMES))
        recommend = Recommend(CONFIG)
        on_off_hysteresis = OnOff(4)

        while True:
            currents = current_monitor.read()
            print(currents)
            estimated = current_combine(currents, CURRENT_TYPES)
            recommended = recommend.current(estimated, commands.tbot.modes.state, quasar)
            charge_rate = on_off_hysteresis.balance(recommended)
            data_logger.tick(currents, recommended, commands.tbot.modes._mode)
            commands.tbot.update_info(currents, estimated, recommended, charge_rate)
            if commands.tbot.modes.state != Mode.OFF:
                quasar.set_charge_rate(charge_rate)
            else:
                if quasar.current != 3:
                    quasar.set_current_setpoint(3)
                quasar.stop_charging()
    except:  # noqa
        CONFIG.logger.exception('Overall:')
        raise
    finally:
        if commands is not None:
            commands.cleanup()
        if quasar is not None:
            quasar.cleanup()
