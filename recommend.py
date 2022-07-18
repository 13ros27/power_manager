from config import Config
from math import ceil, floor
from state import State

class Recommend:
    def __init__(self, config: Config):
        self.config = config

    def _summer_current(self, estimated: float) -> int:
        if abs(estimated) < 3:
            if estimated >= self.config.discharge_rate_frac * 3:
                return -3
            elif estimated <= self.config.charge_rate_frac * 3 - 3:
                return 3
            else:
                return 0
        else:
            part = abs(estimated) % 1
            if estimated < 0:
                if part < 1 - self.config.charge_rate_frac:
                    return -ceil(estimated)
                else:
                    return -floor(estimated)
            else:
                if part < self.config.discharge_rate_frac:
                    return -floor(estimated)
                else:
                    return -ceil(estimated)

    def _winter_current(self, estimated: float) -> int:
        if abs(estimated) < 3:
            if estimated <= self.config.charge_rate_frac * 3 - 3:
                return 3
            else:
                return 0
        else:
            if estimated < 0:
                part = abs(estimated) % 1
                if part < 1 - self.config.charge_rate_frac:
                    return -ceil(estimated)
                else:
                    return -floor(estimated)
            else:
                return -floor(estimated)

    def _preserve_current(self, estimated: float) -> int:
        if estimated >= 0:
            return 0
        else:
            if estimated < -3:
                part = abs(estimated) % 1
                if part < 1 - self.config.charge_rate_frac:
                    return -ceil(estimated)
                else:
                    return -floor(estimated)
            elif estimated <= self.config.charge_rate_frac * 3 - 3:
                return 3
            else:
                return 0

    def current(self, estimated: float, state: State) -> int:
        if state == State.MAX_CHARGE:
            return 32
        elif state == State.SUMMER:
            return self._summer_current(estimated)
        elif state == State.WINTER:
            return self._winter_current(estimated)
        else:
            return self._preserve_current(estimated)
