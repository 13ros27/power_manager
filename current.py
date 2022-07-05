"""Handles everything to do with current monitoring."""
from enum import Enum
from math import ceil, floor
from serial import Serial


class CurrentType(Enum):
    """What type this current expected to be."""

    Source = -1,
    Drain = 1,
    Unknown = 0,


class CurrentMonitor:
    """Monitors the current readings from the Lechacal HAT."""

    def __init__(self, num: int, port: str = '/dev/ttyAMA0',
                 baudrate: int = 38400, timeout: int = 10):
        """Open the serial connection."""
        self.num = num
        self.ser = Serial(port, baudrate, timeout=timeout)

    def read(self) -> [float]:
        """Read one line in from the serial port and reduce it to currents."""
        line = self.ser.readline()
        line = line[:-2]
        line = ''.join(map(chr, line))
        line = line.split(' ')
        if len(line) > self.num + 1:
            return [round(float(p) / 240, 4) for p in line[1:self.num + 1]]
        else:
            raise TypeError(f'Did not expect: {line}')


def current_combine(currents: [float], current_types: [CurrentType]) -> float:
    """Return the number of amps the currents give, Unknown is ignored."""
    return sum([c * ct.value[0] for (c, ct) in zip(currents, current_types)])


def recommended_current(config, total: float) -> int:
    """Recommend a certain amount of current."""
    if abs(total) <= 3:
        step_over = config.rate_frac * 3
        if total >= step_over:
            return -3
        elif total <= -3 + step_over:
            return 3
        else:
            return 0
    else:
        part = abs(total) % 1
        if total < 0:
            if part < 1 - config.rate_frac:
                return -ceil(total)
            else:
                return -floor(total)
        else:
            if part < config.rate_frac:
                return -floor(total)
            else:
                return -ceil(total)