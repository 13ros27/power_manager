from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import PARSEMODE_HTML as HTML
import time

class LiveStatusHandler:
    def __init__(self, tbot, chat_id: int, secs_for: int = 300, mes_id = None):
        self.tbot = tbot
        self.chat_id = chat_id
        self.live_until = time.time() + secs_for
        text = f'<b>LIVE</b>\n{tbot.formatted_current()}'
        if mes_id is None:
            mes = tbot.send_text(text, chat_id, parse_mode=HTML)
            self.mes_id = mes.message_id
        else:
            tbot.edit_message_text(text, chat_id, mes_id, parse_mode=HTML)
            self.mes_id = mes_id
        self.run_out = False

    def updates_on(self) -> list:
        return [0, 1, 2]

    def update(self) -> bool:
        formatted = self.tbot.formatted_current()
        if time.time() > self.live_until:
            message = formatted
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('Continue', callback_data=f'{self.chat_id} {self.mes_id}')]])
            self.run_out = True
        else:
            message = f'<b>LIVE</b>\n{formatted}'
            markup = None
        self.tbot.edit_message_text(message, self.chat_id, self.mes_id, reply_markup=markup, parse_mode=HTML)
        return not self.run_out

    def remove(self):
        if not self.run_out:
            self.tbot.edit_message_text(self.tbot.formatted_current(), self.chat_id, self.mes_id)

class RecommendHandler:
    def __init__(self, tbot, chat_id: int, secs_for = None):
        self.tbot = tbot
        self.chat_id = chat_id
        if secs_for is None:
            self.live_until = None
        else:
            self.live_until = time.time() + secs_for
        self.last_mes_id = self._send_recommendation()

    def updates_on(self) -> list:
        return [2]

    def is_finished(self) -> bool:
        return self.live_until is not None and time.time() > self.live_until

    def update_timer(self, secs_for: int):
        self.live_until = time.time() + secs_for

    def _send_recommendation(self) -> int:
        if self.tbot.info is not None:
            message = f'{self.tbot.info[2]}A'
        else:
            message = 'N/A'
        return self.tbot.send_text(f'Recommendation: {message}', self.chat_id).message_id

    def update(self) -> bool:
        if self.is_finished():
            return False
        else:
            mes_id = self._send_recommendation()
            self.tbot.delete_message(self.chat_id, self.last_mes_id)
            self.last_mes_id = mes_id
            return True

    def remove(self):
        self.tbot.delete_message(self.chat_id, self.last_mes_id)