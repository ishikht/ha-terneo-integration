from dataclasses import dataclass
from typing import List, Optional

import httpx

from .models import TerneoTelemetry

API_BASE_URL = "https://my.terneo.ua/api"
API_V2_BASE_URL = "https://my.terneo.ua/api-v2"


@dataclass
class CloudDevice:
    id: int
    serial_number: str
    name: str
    type: str
    firmware_version: str
    model: str


class CloudService:
    HEADERS_BASE = {"Authorization": ""}

    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._access_token = None
        self.cloud_devices: List[CloudDevice] = []
        self._http_client = None

    async def _get_http_client(self):
        """Lazily initialize the HTTP client."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def initialize(self):
        if await self.auth():
            self.cloud_devices = await self._get_devices() or []

    async def auth(self) -> bool:
        data = await self._send_request(
            "POST", "/login/", json={"email": self._email, "password": self._password}
        )
        if not data:
            return False
        self._access_token = data.get("access_token", None)
        self.HEADERS_BASE["Authorization"] = f"Token {self._access_token}"
        return self._access_token is not None

    def get_name(self, serial_number: str) -> Optional[str]:
        cloud_device = next(
            (d for d in self.cloud_devices if d.serial_number == serial_number), None
        )
        if not cloud_device:
            return None

        return cloud_device.name

    async def get_telemetry(self, serial_number: str) -> Optional[TerneoTelemetry]:
        cloud_device = next(
            (d for d in self.cloud_devices if d.serial_number == serial_number), None
        )
        if not cloud_device:
            return None

        data = await self._send_request("GET", f"/device/{cloud_device.id}/")
        if not data:
            return None
        telemetry_data = data.get("data")
        if not telemetry_data:
            return None

        telemetry = TerneoTelemetry(
            power_off=self._safe_bool_conversion(telemetry_data["device_off"]),
            current_temperature=self._safe_float_conversion(
                telemetry_data["temp_current"]
            ),
            heating=self._safe_bool_conversion(telemetry_data["setpoint_state"]),
            target_temperature=int(telemetry_data["temp_setpoint"]),
        )
        return telemetry

    @staticmethod
    def _safe_float_conversion(value) -> float:
        """Converts string to float safely."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0  # or some default value

    @staticmethod
    def _safe_bool_conversion(value: Optional[bool]) -> bool:
        """Handles nullable booleans."""
        return value is True

    async def set_temperature(self, serial_number: str, temperature: int) -> bool:
        cloud_device = next(
            (d for d in self.cloud_devices if d.serial_number == serial_number), None
        )
        if not cloud_device:
            return False

        response_data = await self._send_request(
            "PUT", f"/device/{cloud_device.id}/setpoint/", json={"value": temperature}
        )
        return response_data and response_data.get("value", None) == temperature

    async def _get_devices(self) -> Optional[List[CloudDevice]]:
        devices_data = await self._send_request("GET", "/device/")

        if not devices_data:
            return None
        return [
            CloudDevice(
                id=device["id"],
                serial_number=device["sn"],
                name=device["name"],
                type=device["type"],
                firmware_version=device.get("version_name", "Unknown"),
                model=self._extract_model_from_image(device.get("image", "")),
            )
            for device in devices_data.get("results", [])
        ]

    @staticmethod
    def _extract_model_from_image(image: str) -> str:
        if not image:
            return "Unknown"
        # Extract the portion after the last slash and before the hyphen.
        model = image.split("/")[-1].split("-")[0].upper()
        return model or "Unknown"

    async def _get_device(self, device_id: int) -> Optional[CloudDevice]:
        device_data = await self._send_request("GET", f"/device/{device_id}/")
        if not device_data:
            return None
        return CloudDevice(
            id=device_data["id"],
            serial_number=device_data["sn"],
            name=device_data["name"],
        )

    async def power_on_off(self, serial_number: str, is_off: bool) -> bool:
        cloud_device = next(
            (d for d in self.cloud_devices if d.serial_number == serial_number), None
        )
        if not cloud_device:
            return False

        response_data = await self._send_request(
            "PUT",
            f"/device/{cloud_device.id}/basic-parameters/",
            base_url=API_V2_BASE_URL,
            json={"power_off": is_off},
        )
        return (
            response_data
            and response_data.get("result", {}).get("power_off", None) == is_off
        )

    async def _send_request(
        self, method: str, endpoint: str, base_url=API_BASE_URL, **kwargs
    ) -> Optional[dict]:
        url = f"{base_url}{endpoint}"
        client = await self._get_http_client()
        headers = self.HEADERS_BASE.copy()
        response = await client.request(method, url, headers=headers, **kwargs)
        if response.status_code != 200:
            return None
        return response.json()
