"""Handles everything to do with current monitoring."""
from enum import Enum
from serial import Serial


class CurrentType(Enum):
    """What type this current expected to be."""

    Source = -1,
    Drain = 1,
    Unknown = 0,


class Current:
    """A simple wrapper type for Current."""

    def __init__(self, amps: float):
        """Links amps to the wrapper type."""
        self.amps = round(amps, 4)

    def __str__(self) -> str:
        """Print this in a human readable way."""
        return f'{self.amps}A'

    def __repr__(self) -> str:
        """Print this in a human readable way."""
        return self.__str__()


class CurrentMonitor:
    """Monitors the current readings from the Lechacal HAT."""

    def __init__(self, num: int, port: str = '/dev/ttyAMA0',
                 baudrate: int = 38400, timeout: int = 10):
        """Open the serial connection."""
        self.num = num
        self.ser = Serial(port, baudrate, timeout=timeout)

    def read(self) -> [Current]:
        """Read one line in from the serial port and reduce it to currents."""
        line = self.ser.readline()
        line = line[:-2]
        line = ''.join(map(chr, line))
        line = line.split(' ')
        if len(line) == 1:
            line = line[0].split(',') # Why did it comma separate?
        if len(line) > self.num + 1:
            return [Current(float(p) / 240) for p in line[1:self.num + 1]]
        else:
            raise TypeError(f'Did not expect: {line}')


def current_combine(currents: [Current], current_types: [CurrentType]) -> int:
    """Return the number of amps the currents give, Unknown is ignored."""
    return sum([c.amps * ct.value[0] for (c, ct) in
                zip(currents, current_types)])
