import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN, SIGNAL_SAUERTEIG_UPDATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    sauerteig_name = entry.data.get("name", "Unbekannter Sauerteig")
    button = SauerteigFuetternButton(hass, entry, sauerteig_name)
    async_add_entities([button])

class SauerteigFuetternButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str) -> None:
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{name} Füttern"
        self._attr_unique_id = f"{entry.entry_id}_fuettern_button"
        self._attr_icon = "mdi:bread-slice-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self._name,
            manufacturer="HSsteuerung",
            model="Sauerteig Manager",
            sw_version="1.0.0",
        )

    @property
    def icon(self) -> str:
        return "mdi:bread-slice-outline"
        
    async def async_press(self) -> None:
        jetzt = dt_util.utcnow() 
        _LOGGER.info("Sauerteig '%s' wurde gefüttert!", self._name)
        self._hass.bus.async_fire(
            f"{DOMAIN}_gefuettert",
            {
                "entity_id": self.entity_id,
                "sauerteig_name": self._name,
                "zeitpunkt": jetzt.isoformat()
            }
        )
        async_dispatcher_send(
            self._hass, 
            f"{SIGNAL_SAUERTEIG_UPDATE}_{self._entry.entry_id}", 
            jetzt
        )
