import logging
from homeassistant.components.sensor import SensorEntity, RestoreEntity
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
    """Setzt die Sensoren auf."""
    entry_id = entry.entry_id
    name = entry.data.get("name", "Sauerteig")

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=name,
        manufacturer="Sauerteig Meister",
        model="Sourdough Starter Tracker",
    )

    entities = [
        SauerteigStateSensor(hass, entry_id, name, device_info),
        SauerteigWeightSensor(hass, entry_id, name, "total_mass_g", "Gesamtgewicht", device_info),
        SauerteigRatioSensor(hass, entry_id, name, device_info)
    ]
    async_add_entities(entities)


class SauerteigStateSensor(SensorEntity):
    """Sensor für den Status (running/paused)."""
    def __init__(self, hass, entry_id, name, device_info):
        self._hass = hass
        self._entry_id = entry_id
        self._attr_name = f"{name} Status"
        self._attr_unique_id = f"{entry_id}_state_sensor"
        self._attr_device_info = device_info

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, f"{DOMAIN}_{self._entry_id}_updated", self._update_callback
            )
        )
        self._update_callback()

    @callback
    def _update_callback(self):
        data = self._hass.data[DOMAIN][self._entry_id]
        self._attr_native_value = data.get("state", "unknown")
        self.async_write_ha_state()


class SauerteigWeightSensor(SensorEntity, RestoreEntity):
    """Sensor für Gewichtsdaten (stellt sich nach Neustart wieder her)."""
    def __init__(self, hass, entry_id, name, key, label, device_info):
        self._hass = hass
        self._entry_id = entry_id
        self._key = key
        self._attr_name = f"{name} {label}"
        self._attr_unique_id = f"{entry_id}_{key}_sensor"
        self._attr_native_unit_of_measurement = "g"
        self._attr_device_info = device_info

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn der Sensor geladen wird."""
        await super().async_added_to_hass()
        
        # Versuche alten Zustand aus der Datenbank zu holen
        old_state = await self.async_get_last_state()
        if old_state and old_state.state not in (None, "unknown", "unavailable"):
            try:
                val = int(float(old_state.state))
                self._hass.data[DOMAIN][self._entry_id][self._key] = val
                self._attr_native_value = val
            except ValueError:
                pass

        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, f"{DOMAIN}_{self._entry_id}_updated", self._update_callback
            )
        )
        self._update_callback()

    @callback
    def _update_callback(self):
        data = self._hass.data[DOMAIN][self._entry_id]
        self._attr_native_value = data.get(self._key, 0)
        self.async_write_ha_state()


class SauerteigRatioSensor(SensorEntity):
    """Sensor zur Berechnung des Fütterungsverhältnisses."""
    def __init__(self, hass, entry_id, name, device_info):
        self._hass = hass
        self._entry_id = entry_id
        self._attr_name = f"{name} Fütterungsverhältnis"
        self._attr_unique_id = f"{entry_id}_ratio_sensor"
        self._attr_icon = "mdi:scale-balance"
        self._attr_device_info = device_info

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, f"{DOMAIN}_{self._entry_id}_updated", self._update_callback
            )
        )
        self._update_callback()

    @callback
    def _update_callback(self):
        data = self._hass.data[DOMAIN][self._entry_id]
        flour = data.get("last_flour_g", 0)
        water = data.get("last_water_g", 0)
        starter = data.get("last_starter_g", 0)

        if starter == 0 or flour == 0 or water == 0:
            self._attr_native_value = "Unbekannt"
            self.async_write_ha_state()
            return

        ratio_flour = round(flour / starter, 1)
        ratio_water = round(water / starter, 1)
        ratio_flour = int(ratio_flour) if ratio_flour.is_integer() else ratio_flour
        ratio_water = int(ratio_water) if ratio_water.is_integer() else ratio_water

        self._attr_native_value = f"1 : {ratio_flour} : {ratio_water}"
        self.async_write_ha_state()
