"""Config information in general."""
from datetime import datetime
import logging
from pathlib import Path


class Config:
    """All the config variables."""

    def __init__(self, path: Path, names: list, current_types: list, day_rate: float, night_rate: float,
                 efficiency: float, night_start: tuple, night_end: tuple):
        """Create all the variables."""
        self.path = path
        self.names = names
        self.current_types = current_types
        self.night_start = night_start
        self.night_end = night_end
        self.efficiency = efficiency
        self.update_day_rate(day_rate)
        self.update_night_rate(night_rate)
        self.setup_logging()

    def update_night_rate(self, night_rate: float):
        self.night_rate = night_rate
        self.discharge_rate = round(night_rate / self.efficiency, 1)
        self.low_night = round(night_rate - 0.1, 1)
        self.high_night = round(night_rate + 0.1, 1)

    def update_day_rate(self, day_rate: float):
        self.day_rate = day_rate
        self.low_day = round(day_rate - 0.1, 1)
        self.high_day = round(day_rate + 0.1, 1)

    def setup_logging(self):
        """Set up all the logging stuff."""
        folder = self.path / Path('logs')
        if not folder.is_dir():
            folder.mkdir()
        logging.basicConfig(
            filename=folder / Path(f'{datetime.now():%Y%m%dT%H%M%S}.log'),
            filemode='w',
            format='%(levelname)s %(asctime)s - %(message)s',
            level=logging.WARNING
        )
        self.logger = logging.getLogger()
