import logging
import voluptuous as vol
from .terneo_net.cloud import CloudService

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from . import DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL, default=""): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

_LOGGER = logging.getLogger(__name__)


class TerneoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            valid_login = await self._validate_login(email, password)
            if valid_login:
                # Set unique ID and check if already configured
                await self.async_set_unique_id(user_input[CONF_EMAIL])

                for entry in self._async_current_entries():
                    if entry.unique_id == user_input[CONF_EMAIL]:
                        return self.async_abort(reason="already_configured_account")

                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    async def _validate_login(email: str, password: str) -> bool:
        try:
            cloud_service = CloudService(email, password)
            return await cloud_service.auth()
        except Exception as ex:
            _LOGGER.error("Failed to validate login: %s", ex)
            return False
