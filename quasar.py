from enum import Enum
from pyModbusTCP.client import ModbusClient
import time

class QuasarStatus(Enum):
    READY = 0
    CHARGING = 1
    WAITING_FOR_CAR_DEMAND = 2
    WAITING_FOR_NEXT_SCHEDULE = 3
    PAUSED_BY_USER = 4
    END_OF_SCHEDULE = 5
    DISCONNECTED = 6
    ERROR = 7
    INQUEUE_POWER_SHARING = 8
    UNCONFIGURED_POWER_SHARING = 9
    INQUEUE_POWER_BOOST = 10
    DISCHARGING = 11

def write(f):
    def wrapper(self, *args, **kwargs):
        if self._disconnected is not None:
            if self._disconnected < time.time():
                self._disconnected = None
                if self._controlling:
                    self.take_control()
            else:
                return None
        f(self, *args, **kwargs)
    return wrapper

class Quasar:
    def __init__(self, host: str, port: int = 502):
        self._client = ModbusClient(host=host, port=port, auto_open=True, auto_close=True)
        self._charging = None
        self.current = None
        self._soc = 0
        self._disconnected = None
        self._controlling = False
        self._last_read_soc = 0.0

    def take_control(self):
        self._controlling = True
        self.write_register(0x51, 1)
        self.stop_charging(True)

    def relinquish_control(self):
        self._controlling = False
        self.stop_charging(True)
        self.write_register(0x51, 0)

    def read_register(self, address: int) -> int:
        reg = self._client.read_holding_registers(address)
        if reg is None:
            return 0
        else:
            return reg[0]

    @write
    def write_register(self, address: int, value: int):
        self._client.write_single_register(address, value)

    @write
    def start_charging(self):
        if self._charging != True:
            self.write_register(0x101, 1)
            self._charging = True

    def stop_charging(self, unchecked: bool = False):
        if unchecked or self._charging != False:
            self.soc
            self.write_register(0x101, 2)
            self._charging = False

    @write
    def set_current_setpoint(self, amps: int):
        if amps >= 0:
            self.write_register(0x102, amps)
        else:
            self.write_register(0x102, 65536 + amps)

    @write
    def set_charge_rate(self, amps: int):
        if self.current == amps:
            return
        else:
            self.current = amps
        if abs(amps) < 3:
            self.stop_charging()
        else:
            self.set_current_setpoint(amps)
            self.start_charging()

    def _read_state_of_charge(self) -> int:
        return self.read_register(0x21A)

    @property
    def soc(self) -> int:
        if self._last_read_soc < time.time():
            self._last_read_soc = time.time() + 120
            reading = self._read_state_of_charge()
            if reading != 0:
                self._soc = reading
        return self._soc

    @property
    def max_available_current(self) -> int:
        return self.read_register(0x200)

    @property
    def max_available_power(self) -> int:
        return self.read_register(0x202)

    @property
    def charger_status(self) -> QuasarStatus:
        return QuasarStatus(self.read_register(0x219))

    def disconnect(self, seconds: int):
        control = self._controlling
        self.relinquish_control()
        self._controlling = control
        self._disconnected = time.time() + seconds

    def cleanup(self):
        self.relinquish_control()
