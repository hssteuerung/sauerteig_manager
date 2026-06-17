import logging
from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

DOMAIN = "sauerteig_manager"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setzt die Number-Entitäten auf."""
    entry_id = entry.entry_id
    name = entry.data.get("name", "Sauerteig")

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=name,
        manufacturer="Sauerteig Meister",
        model="Sourdough Starter Tracker",
    )

    entities = [
        SauerteigIngredientNumber(hass, entry_id, name, "flour_g", "Mehl", 50, device_info),
        SauerteigIngredientNumber(hass, entry_id, name, "water_g", "Wasser", 50, device_info),
        SauerteigIngredientNumber(hass, entry_id, name, "starter_g", "Anstellgut", 10, device_info),
    ]
    async_add_entities(entities)

class SauerteigIngredientNumber(RestoreNumber):
    """Eingabefeld, das seinen Wert nach einem Neustart behält."""

    def __init__(self, hass, entry_id, entry_name, key, label, default_value, device_info):
        self._hass = hass
        self._entry_id = entry_id
        self._key = key
        self._attr_name = f"{entry_name} {label}"
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = device_info
        self._default_value = default_value
        
        self._attr_native_min_value = 0
        self._attr_native_max_value = 500
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "g"
        self._attr_mode = NumberMode.BOX

    async def async_added_to_hass(self):
        """Stellt den alten Zustand aus der HA-Datenbank wieder her."""
        await super().async_added_to_hass()
        
        old_number_data = await self.async_get_last_number_data()
        if old_number_data and old_number_data.native_value is not None:
            val = int(old_number_data.native_value)
            self._attr_native_value = val
        else:
            self._attr_native_value = self._default_value

        # Schreibe den wiederhergestellten Wert zurück in den RAM für andere Berechnungen
        self._hass.data[DOMAIN][self._entry_id][f"last_{self._key}"] = self._attr_native_value

        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, f"{DOMAIN}_{self._entry_id}_updated", self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        current_data = self._hass.data[DOMAIN][self._entry_id]
        self._attr_native_value = current_data.get(f"last_{self._key}", self._attr_native_value)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = int(value)
        self._hass.data[DOMAIN][self._entry_id][f"last_{self._key}"] = int(value)
        self.async_write_ha_state()
