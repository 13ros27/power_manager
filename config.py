"""Config information in general."""
from datetime import datetime
import logging
from pathlib import Path


class Config:
    """All the config variables."""

    def __init__(self, path: Path, names: list, current_types: list, night_rate: float, charge_rate: float,
                 discharge_rate: float, night_start: tuple, night_end: tuple, min_charge: int, max_charge: int):
        """Create all the variables."""
        self.path = path
        self.names = names
        self.current_types = current_types
        self.night_start = night_start
        self.night_end = night_end
        self.charge_rate_frac = charge_rate / night_rate
        self.discharge_rate_frac = discharge_rate / night_rate
        self.min_charge = min_charge
        self.max_charge = max_charge
        self.setup_logging()

    def setup_logging(self):
        """Set up all the logging stuff."""
        folder = self.path / Path('logs')
        if not folder.is_dir():
            folder.mkdir()
        logging.basicConfig(
            filename=folder / Path(f'{datetime.now():%Y%m%dT%H%M%S}.log'),
            filemode='w',
            format='%(levelname)s %(asctime)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger()
