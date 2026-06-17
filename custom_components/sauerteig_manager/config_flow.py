import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

DOMAIN = "sauerteig_manager"

class SauerteigManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            unique_id = user_input["name"].lower().strip().replace(" ", "_")
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Sauerteig: {user_input['name']}", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("name", default="Bernd"): cv.string,
            vol.Required("feeding_interval_hours", default=24): vol.All(vol.Coerce(int), vol.Range(min=1)),
        }), errors=errors)
