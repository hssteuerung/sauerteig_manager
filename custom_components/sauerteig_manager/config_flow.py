from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

class SauerteigConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sauerteig Manager."""
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            name = user_input["name"]
            await self.async_set_unique_id(f"sauerteig_{name.lower()}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("name"): str})
        )
