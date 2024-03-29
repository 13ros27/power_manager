"""Handles datalogging."""
from config import Config
from datetime import datetime
from pathlib import Path
from state import Mode, mode_shorthand
import timing


class DataLogger:
    """Logs the data."""

    def __init__(self, config: Config, freq: int, folder: Path):
        """Create the file to log in and fills in the titles."""
        self.config = config
        self.logger = config.logger
        folder = config.path / folder
        if not folder.is_dir():
            folder.mkdir()
        self.freq = freq
        self.folder = folder
        self.names = config.names
        self.current_types = config.current_types
        self.start_time = timing.second_number()
        self._new_file()
        self.last_tick = None

    def _new_file(self):
        header = 'Time,' + \
            ','.join([f'{n}({t.name})' for (n, t) in zip(self.names, self.current_types)]) + \
            ',Recommended,Mode,SoC,Metadata'
        self.day = timing.comparison_day_number()
        root_filename = f'D{timing.day_number()}'
        i = 1
        while True:
            if i == 1:
                test_filename = f'{root_filename}.csv'
            else:
                test_filename = f'{root_filename}_{i}.csv'
            path = self.folder / test_filename
            file_header = None
            if path.is_file():
                with open(path, 'r') as fp:
                    file_header = fp.readline().replace('\n', '')
                if file_header == header:
                    self.fp = path
                    break
            if not path.is_file():
                self.fp = path
                with open(path, 'x') as fp:
                    fp.write(header)
                break
            i += 1

    def tick(self, currents: list, recommended: int, mode: Mode, soc: int):
        """Log the data if enough time has passed."""
        this_tick = timing.second_number() // self.freq
        if self.last_tick is None or self.last_tick < this_tick:
            self.last_tick = this_tick
            if (timing.comparison_day_number() != self.day
                    and timing.past_this_time(self.config.night_start)):
                self._new_file()
            self._log_to_file(currents, recommended, mode, soc)

    def _log_to_file(self, currents: list, recommended: int, mode: Mode, soc: int):
        with open(self.fp, 'a') as fp:
            mes = str(datetime.now().replace(microsecond=0).isoformat())
            mes += ''.join([f',{c}' for c in currents])
            mes += f',{recommended},{mode_shorthand(mode)},{soc}'
            fp.write(f'\n{mes}')

    def add_metadata(self, metadata: str):
        """Add a bit of metadata to the datalog."""
        with open(self.fp, 'a') as fp:
            fp.write(f',{metadata}')
