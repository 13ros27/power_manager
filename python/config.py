"""Config information in general."""
from current import CurrentType
from pathlib import Path


class Config:
    """All the config variables."""

    def __init__(self, path: Path, names: [str], current_types: [CurrentType]):
        """Create all the variables."""
        self.path = path
        self.names = names
        self.current_types = current_types
