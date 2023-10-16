from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime, timedelta

from .terneo_net.cloud import CloudDevice, CloudService

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL,
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
SUPPORT_HVAC = [HVAC_MODE_HEAT, HVAC_MODE_OFF]

MIN_TEMPERATURE = 5
MAX_TEMPERATURE = 45

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)


async def async_setup_entry(hass, entry, async_add_entities):
    email = hass.data[DOMAIN][CONF_EMAIL]
    password = hass.data[DOMAIN][CONF_PASSWORD]

    cloud = CloudService(email, password)

    try:
        await cloud.initialize()
    except Exception as e:
        _LOGGER.error(f"Error initializing CloudService: {e}")
        return

    entities = [TerneoClimateEntity(device, cloud) for device in cloud.cloud_devices]
    _LOGGER.debug(f"Adding entities: {entities}")
    async_add_entities(entities, True)


class TerneoClimateEntity(ClimateEntity):
    def __init__(self, cloud_device: CloudDevice, cloud_service: CloudService) -> None:
        super().__init__()
        self._last_command_time = datetime.min

        self._target_temperature = None
        self._current_temperature = None

        self._cloud_device = cloud_device
        self._cloud_service = cloud_service

        self._hvac_mode = HVAC_MODE_OFF
        self._hvac_action = CURRENT_HVAC_OFF

        self._attr_name = cloud_device.name
        self._attr_supported_features = SUPPORT_FLAGS
        self._attr_hvac_modes = SUPPORT_HVAC
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 1.0
        self._attr_max_temp = MAX_TEMPERATURE
        self._attr_min_temp = MIN_TEMPERATURE

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._cloud_device.serial_number}"

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return current hvac mode."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return current hvac action."""
        return self._hvac_action

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._cloud_device.serial_number)},
            "name": self._cloud_device.name,
            "manufacturer": "Terneo",
            "model": self._cloud_device.model,
            "sw_version": self._cloud_device.firmware_version
        }

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await self._async_update_telemetry()

    async def _async_update_telemetry(self):
        """Update the state from the provided telemetry data."""
        telemetry = await self._cloud_service.get_telemetry(
            self._cloud_device.serial_number
        )
        if telemetry:
            if telemetry.current_temperature < MIN_TEMPERATURE:
                self._current_temperature = None
            else:
                self._current_temperature = telemetry.current_temperature
            self._target_temperature = telemetry.target_temperature
            self._hvac_mode = (HVAC_MODE_OFF if telemetry.power_off else HVAC_MODE_HEAT)
            if telemetry.power_off:
                self._hvac_action = CURRENT_HVAC_OFF
            else:
                self._hvac_action = (
                    CURRENT_HVAC_HEAT if telemetry.heating else CURRENT_HVAC_IDLE
                )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        try:
            success = await self._cloud_service.set_temperature(self._cloud_device.serial_number, temperature)
            if success:
                self._last_command_time = datetime.now()
                self._target_temperature = temperature
                self.async_write_ha_state()
            else:
                _LOGGER.error(f"Failed to update temperature to {temperature} for device {self.name}")
        except Exception as e:
            _LOGGER.error(f"Error setting temperature to {temperature} for device {self.name}: {e}")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        try:
            is_off = hvac_mode == HVAC_MODE_OFF
            success = await self._cloud_service.power_on_off(self._cloud_device.serial_number, is_off)
            if success:
                self._last_command_time = datetime.now()
                self._hvac_mode = HVAC_MODE_OFF if is_off else HVAC_MODE_HEAT
                self._hvac_action = CURRENT_HVAC_OFF if is_off else CURRENT_HVAC_IDLE
                self.async_write_ha_state()
            else:
                _LOGGER.error(f"Failed to update HVAC mode to {hvac_mode} for device {self.name}")
        except Exception as e:
            _LOGGER.error(f"Error setting HVAC mode to {hvac_mode} for device {self.name}: {e}")

    async def async_update(self):
        """Fetch new state data for this device."""
        if datetime.now() - self._last_command_time > MIN_TIME_BETWEEN_UPDATES:
            await self._async_update_telemetry()
