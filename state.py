from enum import Enum
from config import Config
from quasar import Quasar
import timing

class State(Enum):
    MAX_CHARGE = 1
    SUMMER = 2
    WINTER = 3
    PRESERVE = 4
    LOW_CHARGE = 5

class Mode(Enum):
    MAX_CHARGE = 1
    SUMMER = 2
    WINTER = 3
    PRESERVE = 4
    LOW_CHARGE = 5
    NORMAL = 10

class StateSelect:
    def __init__(self, mode: Mode, config: Config, quasar: Quasar):
        self.mode = Mode.PRESERVE
        self.set_mode(mode)
        self.config = config
        self.quasar = quasar

    def set_mode(self, mode: Mode):
        if self.mode != Mode.NORMAL:
            self.remained_overflowed = False
            self.power_overflow = False
        self.mode = mode

    def _get_state_normal(self):
        if timing.past_this_time(self.config.night_start) and not timing.past_this_time(self.config.night_end):
            soc = self.quasar.soc
            if soc <= self.config.min_charge:
                self.remained_overflowed = True
            if soc < self.config.max_charge:
                return State.MAX_CHARGE
            else:
                return State.PRESERVE
        else:
            if not self.remained_overflowed:
                self.power_overflow = False
            self.remained_overflowed = False
            if self.quasar.soc <= self.config.min_charge:
                self.power_overflow = True
                return State.PRESERVE
            else:
                if self.power_overflow:
                    return State.WINTER
                else:
                    return State.SUMMER

    def _get_state(self, mode: Mode):
        try:
            return State(mode.value)
        except ValueError:
            if mode == Mode.NORMAL:
                return self._get_state_normal()
            else:
                raise ValueError(f"Unexpected mode {mode}")

    @property
    def state(self) -> State:
        return self._get_state(self.mode)
