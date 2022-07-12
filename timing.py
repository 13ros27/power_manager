from datetime import datetime
import time

def past_this_time(time: tuple) -> bool:
    now = datetime.now()
    return time[0] >= now.hour and time[1] >= now.minute

def comparison_day_number() -> int:
    return datetime.now().day

def day_number() -> int:
    return int((time.time() + 3600) // 86400)

def second_number() -> int:
    return int(time.time())
