from dataclasses import dataclass
from typing import Optional

@dataclass
class TerneoTelemetry:
    current_temperature: Optional[float]
    target_temperature: Optional[int]
    heating: Optional[bool]
    power_off: Optional[bool]

    def __str__(self):
        return f"Temp: {self.current_temperature} -> {self.target_temperature}, " \
               f"Heating: {self.heating}, " \
               f"Power off: {self.power_off}"


@dataclass
class TerneoDevice:
    ip: str
    serial_number: str

    def __eq__(self, other):
        if isinstance(other, TerneoDevice):
            return self.ip == other.ip and self.serial_number == other.serial_number
        return False

    def __str__(self) -> str:
        return f"IP: {self.ip}, sn: {self.serial_number}"
