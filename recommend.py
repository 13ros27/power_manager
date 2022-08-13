from config import Config
from math import ceil, floor
from state import State
import timing

def energy_price(config: Config):
    if timing.past_this_time(config.night_start) and not timing.past_this_time(config.night_end):
        return config.night_rate
    else:
        return config.day_rate

class Recommend:
    def __init__(self, config: Config):
        self.config = config

    def round_estimation(self, estimated: float, frac: float, minimum: int = 3) -> int:
        positive = abs(estimated)
        value = 0
        if positive > minimum:
            part = positive % 1
            if part < frac:
                value = floor(positive)
            else:
                value = ceil(positive)
        elif positive >= minimum - frac * minimum:
            value = minimum
        else:
            value = 0
        if estimated >= 0:
            return -value
        else:
            return value

    def current(self, estimated: float, state: State) -> int:
        cur_price = energy_price(self.config)
        if estimated <= 0:
            if cur_price < state.charge_cost_limit:
                return 32
            else:
                return self.round_estimation(estimated, min(state.charge_cost_limit / cur_price, 1), 3)
        else:
            if cur_price < state.stored_discharge_value:
                return 0
            else:
                return self.round_estimation(estimated, 1 - min(state.stored_discharge_value / cur_price, 1), state.min_discharge_rate)
