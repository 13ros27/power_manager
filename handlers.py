from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import PARSEMODE_HTML as HTML
from state import Mode
import timing

class ChangeHandler:
    def should_update(self) -> bool:
        return False

    def update(self) -> bool:
        return True

    def remove(self):
        pass

class LiveStatusHandler(ChangeHandler):
    def __init__(self, tbot, chat_id: int, secs_for: int = 300, mes_id = None):
        self.tbot = tbot
        self.chat_id = chat_id
        self.live_until = timing.second_number() + secs_for
        self.last_formatted = tbot.formatted_current()
        mode = self.mode_shorthand(tbot.modes._mode)
        text = f'<b>LIVE ({mode})</b>\n{self.last_formatted}'
        if mes_id is None:
            mes = tbot.send_text(text, chat_id, parse_mode=HTML)
            self.mes_id = mes.message_id
        else:
            tbot.edit_message_text(text, chat_id, mes_id, parse_mode=HTML)
            self.mes_id = mes_id
        self.run_out = False

    def mode_shorthand(self, mode: Mode) -> str:
        if mode == Mode.OFF:
            return 'O'
        elif mode == Mode.CHARGE_ONLY:
            return 'CO'
        elif mode == Mode.CHARGE_DISCHARGE:
            return 'CD'
        elif mode == Mode.AUTO:
            return 'A'
        else:
            return '?'

    def should_update(self) -> bool:
        return self.tbot.formatted_current() != self.last_formatted

    def update(self) -> bool:
        self.last_formatted = self.tbot.formatted_current()
        if timing.second_number() > self.live_until:
            message = self.last_formatted
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('Continue', callback_data=f'{self.chat_id} {self.mes_id}')]])
            self.run_out = True
        else:
            mode = self.mode_shorthand(self.tbot.modes._mode)
            message = f'<b>LIVE ({mode})</b>\n{self.last_formatted}'
            markup = None
        self.tbot.edit_message_text(message, self.chat_id, self.mes_id, reply_markup=markup, parse_mode=HTML)
        return not self.run_out

    def remove(self):
        if not self.run_out:
            self.tbot.edit_message_text(self.tbot.formatted_current(), self.chat_id, self.mes_id)

class RecommendHandler(ChangeHandler):
    def __init__(self, tbot, chat_id: int, secs_for = None):
        self.tbot = tbot
        self.chat_id = chat_id
        if secs_for is None:
            self.live_until = None
        else:
            self.live_until = timing.second_number() + secs_for
        self.last_mes_id = self._send_recommendation()

    def should_update(self) -> bool:
        return self.tbot.info.item_has_changed('recommended')

    def is_finished(self) -> bool:
        return self.live_until is not None and timing.second_number() > self.live_until

    def update_timer(self, secs_for: int):
        self.live_until = timing.second_number() + secs_for

    def _send_recommendation(self):
        if self.tbot.info['recommended'] is not None:
            message = f'{self.tbot.info["recommended"]}A'
        else:
            message = 'N/A'
        mes = self.tbot.send_text(f'Recommendation: {message}', self.chat_id)
        if mes is None:
            return None
        else:
            return mes.message_id

    def update(self) -> bool:
        if self.is_finished():
            return False
        else:
            mes_id = self._send_recommendation()
            if self.last_mes_id is not None:
                self.tbot.delete_message(self.chat_id, self.last_mes_id)
            self.last_mes_id = mes_id
            return True

    def remove(self):
        self.tbot.delete_message(self.chat_id, self.last_mes_id)
