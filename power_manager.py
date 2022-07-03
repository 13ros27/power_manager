"""Datalogs the current readings."""
from datetime import datetime
from enum import Enum
from os import mkdir
from pathlib import Path
import serial
import time

ser = serial.Serial('/dev/ttyAMA0', baudrate=38400, timeout=10)


class CurrentType(Enum):
    """What type this current expected to be."""

    Source = 1,
    Drain = -1,
    Unknown = 0,


class Current:
    """A simple wrapper type for Current."""

    def __init__(self, amps: int):
        """Links amps to the wrapper type."""
        self.amps = amps


class CurrentMonitor:
    """Monitors the current readings from the Lechacal HAT."""

    def __init__(self, num: int, port: str = '/dev/ttyAMA0',
                 baudrate: int = 38400, timeout: int = 10):
        """Open the serial connection."""
        self.num = num
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

    def read(self) -> [Current]:
        """Read one line in from the serial port and reduce it to currents."""
        line = ser.readline().split(' ')
        if len(line) > self.num + 1:
            return [Current(float(p) / 240) for p in line[1:self.num + 1]]
        else:
            print(len(line))  # TODO: Figure out what to do here


class DataLogger:
    """Logs the data."""

    def __init__(self, freq: int, folder: Path, names: [str],
                 types: [CurrentType]):
        """Create the file to log in and fills in the titles."""
        if not folder.is_dir():
            mkdir(folder)
        self.freq = freq
        self.folder = folder
        self.current_types = types
        self.start_time = time.time()
        self._new_file(names)

    def _new_file(self, names: [str]):
        day = self.start_time // 86400
        root_filename = f'D{day}'
        i = 1
        while True:
            if i == 1:
                test_filename = f'{root_filename}.csv'
            else:
                test_filename = f'{root_filename}_{i}.csv'
            path = self.folder / test_filename
            if not path.is_file():
                self.fp = path
                with open(path, 'w') as fp:
                    mes = f'Time' + ''.join([f',{n}({t})' for (n, t) in
                                             zip(names, self.current_types)])
                    fp.write(mes)

    def tick(self, currents: [Current]):
        """Log the data if enough time has passed."""
        this_tick = time.time() // self.freq
        if self.last_tick is None or self.last_tick < this_tick:
            self.last_tick = this_tick
            self._log_to_file(currents)

    def _log_to_file(self, currents: [Current]):
        with open(self.fp, 'a') as fp:
            mes = str(datetime.now().isoformat())
            mes += ''.join([f',{c.amps}' for c in currents])
            fp.write(mes)


NAMES = ['Solar', 'House', 'HeatPump', 'Outside', 'Grid']
CURRENT_TYPES = [
    CurrentType.Source,
    CurrentType.Drain,
    CurrentType.Drain,
    CurrentType.Unknown,
    CurrentType.Unknown,
]
data_logger = DataLogger(15, Path('/home/pi/data'), NAMES, CURRENT_TYPES)
print(data_logger)
current_monitor = CurrentMonitor(len(NAMES))
print(current_monitor)

while True:
    currents = current_monitor.read()
    print(currents)
    data_logger.tick(currents)
