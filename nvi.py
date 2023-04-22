"""Stores information in a json file, acting like a dictionary."""
import json
from pathlib import Path


class NonVolatileInformation:
    """Used for storing chat information in a json file."""

    def __init__(self, file: Path):
        """Get the information currently stored in the file."""
        self.file = file
        with open(self.file, 'r') as fp:
            self._info = json.load(fp)
        self.token = self._info['token']

    def add_chat(self, chat_id: int):
        """Create a new chat with default information."""
        self._info['chats'][str(chat_id)] = {'recommend': False}
        self._update()

    def __getitem__(self, chat_id: int) -> dict:
        """Get the information about a given chat."""
        return self._info['chats'][str(chat_id)]

    def setitem(self, chat_id: int, setting: str, new_val):
        """Set a piece of information about a given chat."""
        self._info['chats'][str(chat_id)][setting] = new_val
        self._update()

    def get_general(self, name: str, default: int):
        if self._info.get('general') is None:
            self._info['general'] = {}
            self._update()
        if (self._info['general'].get(name) is None):
            return default
        else:
            return self._info['general'][name]

    def set_general(self, name: str, value):
        if self._info.get('general') is None:
            self._info['general'] = {}
        self._info['general'][name] = value
        self._update()

    def _update(self):
        with open(self.file, 'w') as fp:
            json.dump(self._info, fp)

    def is_valid(self, chat_id: int):
        """Check if a given chat id is validated."""
        return str(chat_id) in self._info['chats']

    def __iter__(self):
        """Iterate through the chat ids."""
        return iter(self._info['chats'])
