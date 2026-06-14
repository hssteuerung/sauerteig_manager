import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_SAUERTEIG_UPDATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    sauerteig_name = entry.data.get("name", "Unbekannter Sauerteig")
    sensor = SauerteigZuletztGefuettertSensor(hass, entry, sauerteig_name)
    async_add_entities([sensor])

class SauerteigZuletztGefuettertSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str) -> None:
        self._hass = hass
        self._entry = entry
        self._name = name
        self._state = None
        self._attr_name = f"{name} Letzte Fütterung"
        self._attr_unique_id = f"{entry.entry_id}_letzte_fuetterung_sensor"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self._name,
            manufacturer="HSsteuerung",
            model="Sauerteig Manager",
            sw_version="1.0.0",
        )

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                f"{SIGNAL_SAUERTEIG_UPDATE}_{self._entry.entry_id}",
                self._handle_value_update,
            )
        )

    @callback
    def _handle_value_update(self, zeitpunkt: datetime) -> None:
        self._state = zeitpunkt
        self.async_write_ha_state()
