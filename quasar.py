from enum import Enum
from pyModbusTCP.client import ModbusClient

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

class Quasar:
    def __init__(self, host: str, take_control: bool = True, port: int = 502):
        self._client = ModbusClient(host=host, port=port, auto_open=True, auto_close=True)
        if take_control:
            self.take_control()
        self.write_register(0x53, 0)  # Make sure it is in current mode
        self.stop_charging()
        self.current = None

    def take_control(self):
        self.write_register(0x51, 1)

    def relinquish_control(self):
        self.write_register(0x51, 0)

    def read_register(self, address: int) -> int:
        return self._client.read_holding_registers(address)[0]

    def write_register(self, address: int, value: int):
        self._client.write_single_register(address, value)

    def start_charging(self):
        if not self._charging:
            self.write_register(0x101, 1)
            self._charging = True

    def stop_charging(self):
        print('hi')
        if self._charging:
            print('hello')
            self.write_register(0x101, 2)
            self._charging = False

    def set_current_setpoint(self, amps: int):
        if amps >= 0:
            self.write_register(0x102, amps)
        else:
            self.write_register(0x102, 65536 + amps)

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

    def read_state_of_charge(self) -> int:
        return self.read_register(0x21A)

    def read_max_available_current(self) -> int:
        return self.read_register(0x200)

    def read_max_available_power(self) -> int:
        return self.read_register(0x202)

    def read_charger_status(self) -> QuasarStatus:
        return QuasarStatus(self.read_register(0x219))

    def cleanup(self):
        self.stop_charging()
        self.relinquish_control()