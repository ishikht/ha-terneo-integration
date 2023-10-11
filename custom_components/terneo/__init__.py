from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from homeassistant.const import CONF_PASSWORD, CONF_EMAIL

DOMAIN = "terneo"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN] = {
        CONF_EMAIL: entry.data[CONF_EMAIL],
        CONF_PASSWORD: entry.data[CONF_PASSWORD],
    }

    # Now you load the platforms that you want to initialize:
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Handle unloading the entry (e.g., when the user removes it)
    await hass.config_entries.async_forward_entry_unload(entry, "climate")
    return True
