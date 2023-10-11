from __future__ import annotations

import logging
from .terneo_net.cloud import CloudDevice, CloudService

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL,
    UnitOfTemperature,
)

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
SUPPORT_HVAC = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


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
        self._cloud_device = cloud_device
        self._cloud_service = cloud_service

        self._hvac_mode = CURRENT_HVAC_OFF
        self._name = cloud_device.name

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await self._async_update_telemetry()

    async def _async_update_telemetry(self):
        """Update the state from the provided telemetry data."""
        telemetry = await self._cloud_service.get_telemetry(
            self._cloud_device.serial_number
        )
        if telemetry:
            self._current_temperature = telemetry.current_temperature
            self._target_temperature = telemetry.target_temperature
            self._hvac_mode = (
                CURRENT_HVAC_HEAT if telemetry.heating else CURRENT_HVAC_OFF
            )

    @property
    def name(self):
        """Return the name of this Thermostat."""
        return self._name

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
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_HVAC

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return UnitOfTemperature.CELSIUS

    async def async_update(self):
        """Fetch new state data for this device."""
        await self._async_update_telemetry()
