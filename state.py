from enum import Enum
from config import Config
from quasar import Quasar

# class State(Enum):
#     MAX_CHARGE = 1
#     SUMMER = 2
#     WINTER = 3
#     PRESERVE = 4
#     LOW_CHARGE = 5

# class Mode(Enum):
#     MAX_CHARGE = 1
#     SUMMER = 2
#     WINTER = 3
#     PRESERVE = 4
#     LOW_CHARGE = 5
#     NORMAL = 10

# class StateSelect:
#     def __init__(self, mode: Mode, config: Config, quasar: Quasar):
#         self.mode = Mode.PRESERVE
#         self.set_mode(mode)
#         self.config = config
#         self.quasar = quasar

#     def set_mode(self, mode: Mode):
#         if self.mode != Mode.NORMAL:
#             self.remained_overflowed = False
#             self.power_overflow = False
#         self.mode = mode

#     def _get_state_normal(self):
#         if timing.past_this_time(self.config.night_start) and not timing.past_this_time(self.config.night_end):
#             soc = self.quasar.soc
#             if soc <= self.config.min_charge:
#                 self.remained_overflowed = True
#             if soc < self.config.max_charge:
#                 return State.MAX_CHARGE
#             else:
#                 return State.PRESERVE
#         else:
#             if not self.remained_overflowed:
#                 self.power_overflow = False
#             self.remained_overflowed = False
#             if self.quasar.soc <= self.config.min_charge:
#                 self.power_overflow = True
#                 return State.PRESERVE
#             else:
#                 if self.power_overflow:
#                     return State.WINTER
#                 else:
#                     return State.SUMMER

#     def _get_state(self, mode: Mode):
#         try:
#             return State(mode.value)
#         except ValueError:
#             if mode == Mode.NORMAL:
#                 return self._get_state_normal()
#             else:
#                 raise ValueError(f"Unexpected mode {mode}")

#     @property
#     def state(self) -> State:
#         return self._get_state(self.mode)

class UserSettings:
    def __init__(self, config: Config):
        self.charge_cost_limit = 0
        self.stored_discharge_value = config.high_day
        self.min_discharge_rate = 3

class State:
    def __init__(self, user_settings: UserSettings, charge_cost_limit, stored_discharge_value, min_discharge_rate):
        self.user_settings = user_settings
        self._charge_cost_limit = charge_cost_limit
        self._stored_discharge_value = stored_discharge_value
        self._min_discharge_rate = min_discharge_rate

    @property
    def charge_cost_limit(self) -> float:
        if isinstance(self._charge_cost_limit, (int, float)):
            return self._charge_cost_limit
        else:
            return self._charge_cost_limit(self.user_settings)

    @property
    def stored_discharge_value(self) -> float:
        if isinstance(self._stored_discharge_value, (int, float)):
            return self._stored_discharge_value
        else:
            return self._stored_discharge_value(self.user_settings)

    @property
    def min_discharge_rate(self) -> int:
        if isinstance(self._min_discharge_rate, int):
            return self._min_discharge_rate
        else:
            return self._min_discharge_rate(self.user_settings)

class Auto:
    def __init__(self, config: Config):
        self.config = config

    @property
    def charge_cost_limit(self) -> float:
        return 0.0

    @property
    def stored_discharge_value(self) -> float:
        return self.config.high_day

class Mode(Enum):
    OFF = 0
    CHARGE_ONLY = 1
    CHARGE_DISCHARGE = 2
    AUTO = 3

class Modes:
    def __init__(self, config: Config, mode: Mode, quasar: Quasar):
        self.user_settings = UserSettings(config)
        self.quasar = quasar
        auto = Auto(config)
        self.modes = {
            Mode.OFF: None,
            Mode.CHARGE_ONLY: State(self.user_settings, lambda us: us.charge_cost_limit, config.high_day, lambda us: us.min_discharge_rate),
            Mode.CHARGE_DISCHARGE: State(self.user_settings, lambda us: us.charge_cost_limit, lambda us: us.stored_discharge_value, lambda us: us.min_discharge_rate),
            Mode.AUTO: State(self.user_settings, auto.charge_cost_limit, auto.stored_discharge_value, 3)
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
