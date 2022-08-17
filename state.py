from enum import Enum
from config import Config
from quasar import Quasar
import timing

class UserSettings:
    def __init__(self, config: Config):
        self.config = config
        self.charge_cost_limit = 0.0
        self.discharge_value = config.low_day
        self.min_discharge_rate = 3
        self.max_paid_soc = config.summer_max_charge
        self.min_discharge_soc = config.min_charge

    def ccl(self):
        return self.charge_cost_limit

    def sdv(self):
        return self.discharge_value

    def mdr(self):
        return self.min_discharge_rate

    def max_sb(self):
        if self.max_paid_soc == -1:
            return []
        else:
            return [(self.max_paid_soc, 0.0)]

    def min_sb(self):
        if self.min_discharge_soc == -1:
            return []
        else:
            return [(self.min_discharge_soc, self.config.high_day)]

class State:
    def __init__(self, charge_cost_limit, discharge_value, min_discharge_rate, max_soc_boundaries, min_soc_boundaries):
        self._charge_cost_limit = charge_cost_limit
        self._discharge_value = discharge_value
        self._min_discharge_rate = min_discharge_rate
        self._max_soc_boundaries = max_soc_boundaries
        self._min_soc_boundaries = min_soc_boundaries

    @property
    def charge_cost_limit(self) -> float:
        if isinstance(self._charge_cost_limit, (int, float)):
            return self._charge_cost_limit
        else:
            return self._charge_cost_limit()

    @property
    def discharge_value(self) -> float:
        if isinstance(self._discharge_value, (int, float)):
            return self._discharge_value
        else:
            return self._discharge_value()

    @property
    def min_discharge_rate(self) -> int:
        if isinstance(self._min_discharge_rate, int):
            return self._min_discharge_rate
        else:
            return self._min_discharge_rate()

    @property
    def max_soc_bounds(self) -> list:
        if isinstance(self._max_soc_boundaries, list):
            return self._max_soc_boundaries
        else:
            return self._max_soc_boundaries()

    @property
    def min_soc_bounds(self) -> list:
        if isinstance(self._min_soc_boundaries, list):
            return self._min_soc_boundaries
        else:
            return self._min_soc_boundaries()


class Auto:
    def __init__(self, config: Config, quasar: Quasar):
        self.config = config
        self.quasar = quasar
        self.winter_day = None

    def charge_cost_limit(self) -> float:
        return self.config.high_night

    def discharge_value(self) -> float:
        day_num = timing.comparison_day_number()
        if self.quasar.soc <= self.config.min_charge:
            self.winter_day = day_num
        if self.winter_day != day_num: # SUMMER
            return self.config.discharge_rate
        else: # WINTER
            return self.config.low_day

    def max_soc_bounds(self) -> list:
        if self.winter_day != timing.comparison_day_number(): # SUMMER
            return [(self.config.summer_max_charge, self.config.low_night)]
        else: # WINTER
            return [(self.config.winter_max_charge, self.config.low_night)] # TODO: Change this to 90%

    def min_soc_bounds(self) -> list:
        return [(self.config.min_charge, self.config.high_day)]

class Mode(Enum):
    OFF = 0
    CHARGE_ONLY = 1
    CHARGE_DISCHARGE = 2
    MAX_CHARGE = 3
    AUTO = 4

class Modes:
    def __init__(self, config: Config, mode: Mode, quasar: Quasar):
        user_settings = UserSettings(config)
        self.user_settings = user_settings
        self.quasar = quasar
        auto = Auto(config, quasar)
        self.modes = {
            Mode.OFF: State(user_settings.ccl, user_settings.sdv, user_settings.mdr, user_settings.max_sb, user_settings.min_sb), # Mode.OFF shows up as CHARGE_DISCHARGE for recommendation
            Mode.CHARGE_ONLY: State(user_settings.ccl, config.high_day, 3, user_settings.max_sb, []),
            Mode.CHARGE_DISCHARGE: State(user_settings.ccl, user_settings.sdv, user_settings.mdr, user_settings.max_sb, user_settings.min_sb),
            Mode.MAX_CHARGE: State(user_settings.ccl, config.high_day, 3, [], []),
            Mode.AUTO: State(auto.charge_cost_limit, auto.discharge_value, 3, auto.max_soc_bounds, auto.min_soc_bounds)
        }
        self._mode = mode

    def set_mode(self, new_mode: Mode):
        if new_mode == Mode.OFF:
            self.quasar.relinquish_control()
        elif self._mode == Mode.OFF:
            self.quasar.take_control()
        self._mode = new_mode

    @property
    def state(self) -> State:
        return self.modes[self._mode]
