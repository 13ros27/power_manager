"""Handles datalogging."""
from current import Current, CurrentType
from datetime import datetime
from os import mkdir
from pathlib import Path
import time


class DataLogger:
    """Logs the data."""

    def __init__(self, freq: int, folder: Path, names: [str],
                 types: [CurrentType]):
        """Create the file to log in and fills in the titles."""
        if not folder.is_dir():
            mkdir(folder)
        self.freq = freq
        self.folder = folder
        self.names = names
        self.current_types = types
        self.start_time = time.time()
        self._new_file()
        self.last_tick = None

    def _new_file(self):
        self.day = int(time.time() // 86400)
        root_filename = f'D{self.day}'
        i = 1
        while True:
            if i == 1:
                test_filename = f'{root_filename}.csv'
            else:
                test_filename = f'{root_filename}_{i}.csv'
            path = self.folder / test_filename
            if not path.is_file():
                self.fp = path
                with open(path, 'x') as fp:
                    mes = 'Time'
                    mes += ''.join([f',{n}({t.name})' for (n, t) in
                                    zip(self.names, self.current_types)])
                    fp.write(mes + '\n')
                break
            i += 1

    def tick(self, currents: [Current]):
        """Log the data if enough time has passed."""
        this_tick = time.time() // self.freq
        if self.last_tick is None or self.last_tick < this_tick:
            self.last_tick = this_tick
            if int(time.time() // 86400) != self.day:
                self._new_file()
            self._log_to_file(currents)

    def _log_to_file(self, currents: [Current]):
        with open(self.fp, 'a') as fp:
            mes = str(datetime.now().replace(microsecond=0).isoformat())
            mes += ''.join([f',{c.amps}' for c in currents])
            fp.write(mes+'\n')
