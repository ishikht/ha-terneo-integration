import asyncio
import json
import socket
import threading
from typing import Callable, List, Optional

import httpx
from terneo_net.models import TerneoDevice, TerneoTelemetry

API_URI = "http://{}/api.cgi"
UDP_PORT = 23500


class LocalService:
    def __init__(self):
        self._online_devices: List[TerneoDevice] = []
        self._semaphore = asyncio.Semaphore(1)
        self._discovery_thread = None
        self._udp_socket = None
        self._is_discovering = False
        self.on_device_discovered: List[Callable[[TerneoDevice], None]] = []

    async def initialize(self):
        self._start_discovery()
        await asyncio.sleep(120)  # 2 minutes
        self._stop_discovery()

    async def get_telemetry(self, serial_number: str) -> Optional[TerneoTelemetry]:
        device = next(
            (d for d in self._online_devices if d.serial_number == serial_number), None
        )
        if not device:
            return None

        async with self._semaphore, httpx.AsyncClient() as client:
            response = await client.post(API_URI.format(device.ip), json={"cmd": 4})
            if response.status_code != 200:
                return None
            data = response.json()
            telemetry = self._parse_telemetry_data(data)
            return telemetry

    async def set_temperature(self, serial_number: str, temperature: int) -> bool:
        device = next(
            (d for d in self._online_devices if d.serial_number == serial_number), None
        )
        if not device:
            return False

        async with self._semaphore, httpx.AsyncClient() as client:
            response = await client.post(
                API_URI.format(device.ip),
                json={"sn": device.serial_number, "par": [[5, 1, str(temperature)]]},
            )
            data = response.json()
            return data.get("success", False)

    async def power_on(self, serial_number: str) -> bool:
        return await self._power_on_off(serial_number, False)

    async def power_off(self, serial_number: str) -> bool:
        return await self._power_on_off(serial_number, True)

    async def _power_on_off(self, serial_number: str, is_off: bool) -> bool:
        device = next(
            (d for d in self._online_devices if d.serial_number == serial_number), None
        )
        if not device:
            return False

        async with self._semaphore, httpx.AsyncClient() as client:
            response = await client.post(
                API_URI.format(device.ip),
                json={
                    "sn": device.serial_number,
                    "par": [[125, 7, "1" if is_off else "0"]],
                },
            )
            data = response.json()
            return data.get("success", False)

    def _start_discovery(self):
        self._stop_discovery()
        self._is_discovering = True
        self._online_devices.clear()
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.bind(("", UDP_PORT))
        self._discovery_thread = threading.Thread(target=self._udp_listener)
        self._discovery_thread.start()

    def _stop_discovery(self):
        self._is_discovering = False
        if self._udp_socket:
            self._udp_socket.close()
            self._udp_socket = None
        self._discovery_thread = None

    def _udp_listener(self):
        while self._is_discovering:
            try:
                data, addr = self._udp_socket.recvfrom(1024)  # 1024 is buffer size
                # return_data = data.decode('ASCII')
                ip = addr[0]
                device = self._parse_discovery_data(data.decode())
                if device is None:
                    return

                device.ip = ip
                if device not in self._online_devices:
                    self._online_devices.append(device)
                    for callback in self.on_device_discovered:
                        callback(device)
            except:
                if not self._is_discovering:
                    return

    @staticmethod
    def _parse_discovery_data(json_str) -> Optional[TerneoDevice]:
        try:
            # hardware = data.get("hw"),
            # cloud = data.get("cloud"),
            # connection = data.get("connection"),
            # wifi_signal = data.get("wifi"),
            # display = data.get("display")

            data = json.loads(json_str)
            return TerneoDevice(ip=data.get("ip"), serial_number=data.get("sn"))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _parse_telemetry_data(data: dict) -> TerneoTelemetry:
        # Parsing current_temperature
        current_temp_value = data.get("t.1")
        if current_temp_value:
            current_temperature = int(current_temp_value) / 16.0
        else:
            current_temperature = None

        # Parsing target_temperature
        target_temp_value = data.get("t.5")
        if target_temp_value:
            target_temperature = int(target_temp_value) // 16
        else:
            target_temperature = None

        return TerneoTelemetry(
            current_temperature=current_temperature,
            target_temperature=target_temperature,
            heating=data.get("f.0") == "1",
            power_off=data.get("f.16") == "1",
        )
