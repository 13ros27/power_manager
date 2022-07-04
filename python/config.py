"""Config information in general."""
from current import CurrentType
from datetime import datetime
import logging
from pathlib import Path


class Config:
    """All the config variables."""

    def __init__(self, path: Path, names: [str], current_types: [CurrentType]):
        """Create all the variables."""
        self.path = path
        self.names = names
        self.current_types = current_types
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
