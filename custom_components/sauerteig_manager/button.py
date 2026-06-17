import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

DOMAIN = "sauerteig_manager"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setzt den Füttern-Button auf."""
    entry_id = entry.entry_id
    name = entry.data.get("name", "Sauerteig")

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=name,
        manufacturer="Sauerteig Meister",
        model="Sourdough Starter Tracker",
    )

    async_add_entities([SauerteigFeedButton(hass, entry, device_info)])

class SauerteigFeedButton(ButtonEntity):
    """Button, um den Sauerteig zu füttern."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device_info: DeviceInfo) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_name = f"{entry.data.get('name', 'Sauerteig')} Füttern"
        self._attr_unique_id = f"{entry.entry_id}_feed_button"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Wird aufgerufen, wenn der Button gedrückt wird."""
        await self._hass.services.async_call(
            DOMAIN,
            "feed",
            {"entry_id": self._entry.entry_id},
            blocking=True
        )
