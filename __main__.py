from commands import TeleCommands
from config import Config
from current import CurrentMonitor, CurrentType, current_combine
from datalogger import DataLogger
from hysteresis import OnOff
from pathlib import Path
from quasar import Quasar
from recommend import Recommend
from state import State
import timing


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
    CONFIG = Config(Path("/home/pi/power_manager"), NAMES, CURRENT_TYPES, 30.7, 7.5, 13.0, (0, 30), (1, 30))
    commands = None
    quasar = None
    try:
        data_logger = DataLogger(CONFIG, 15, Path('data'))
        quasar = Quasar(QUASAR_ADDR)
        commands = TeleCommands(CONFIG, data_logger, quasar)
        current_monitor = CurrentMonitor(len(NAMES))
        state = State.PRESERVE
        recommend = Recommend(CONFIG, state)
        on_off_hysteresis = OnOff(4)

        while True:
            if timing.past_this_time(CONFIG.night_start) and not timing.past_this_time(CONFIG.night_end):
                state = State.MAX_CHARGE
            else:
                state = State.PRESERVE
            currents = current_monitor.read()
            print(currents)
            estimated = current_combine(currents, CURRENT_TYPES)
            recommended = recommend.current(estimated, state)
            charge_rate = on_off_hysteresis.balance(recommended)
            data_logger.tick(currents, recommended, state)
            commands.tbot.update_info(currents, estimated, recommended, charge_rate)
            if commands.following:
                quasar.set_charge_rate(charge_rate)
    except:  # noqa
        CONFIG.logger.exception('Overall:')
        raise
    finally:
        if commands is not None:
            commands.cleanup()
        if quasar is not None:
            quasar.cleanup()
