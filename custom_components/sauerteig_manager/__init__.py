import datetime
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

DOMAIN = "sauerteig_manager"
_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button", "number"]

# Schlüssel für die Service-Parameter
ATTR_ENTRY_ID = "entry_id"
ATTR_FLOUR = "flour_g"
ATTR_WATER = "water_g"
ATTR_STARTER = "starter_g"

# Erweitertes Schema für die Services (z.B. für das Dashboard oder Automatisierungen)
SERVICE_FEED_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Optional(ATTR_FLOUR): cv.positive_int,
    vol.Optional(ATTR_WATER): cv.positive_int,
    vol.Optional(ATTR_STARTER): cv.positive_int,
})

SERVICE_BASE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt den Sauerteig-Manager über einen Config Entry auf."""
    hass.data.setdefault(DOMAIN, {})
    
    entry_id = entry.entry_id
    name = entry.data.get("name")
    interval = entry.data.get("feeding_interval_hours", 24)
    
    # Standardwerte aus den Optionen/Daten holen (falls im ConfigFlow definiert, sonst Default 50g)
    default_flour = entry.data.get("default_flour_g", 50)
    default_water = entry.data.get("default_water_g", 50)
    default_starter = entry.data.get("default_starter_g", 10)
    
    now = dt_util.now()
    expires = now + datetime.timedelta(hours=interval)
    
    # Speicherstruktur um die Zutaten-Mengen erweitert
    hass.data[DOMAIN][entry_id] = {
        "name": name,
        "interval": interval,
        "state": "running",
        "last_fed": now.isoformat(),
        "expires_at": expires.isoformat(),
        "remaining_seconds": interval * 3600,
        # Hier werden die aktuellen Mengen der letzten Fütterung gespeichert
        "last_flour_g": default_flour,
        "last_water_g": default_water,
        "last_starter_g": default_starter,
        "total_mass_g": default_flour + default_water + default_starter
    }
    
    if not hass.services.has_service(DOMAIN, "feed"):
        setup_services(hass)
        
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entfernt einen Config Entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, "feed")
        hass.services.async_remove(DOMAIN, "pause")
        hass.services.async_remove(DOMAIN, "resume")
        hass.data.pop(DOMAIN, None)
        
    return unload_ok

def setup_services(hass: HomeAssistant):
    """Registriert die Services für Home Assistant."""
    
    def get_target_entries(call: ServiceCall):
        target_entry_id = call.data.get(ATTR_ENTRY_ID)
        if target_entry_id:
            return [target_entry_id] if target_entry_id in hass.data[DOMAIN] else []
        return hass.data[DOMAIN].keys()

    async def handle_feed(call: ServiceCall):
        for entry_id in get_target_entries(call):
            data = hass.data[DOMAIN][entry_id]
            now = dt_util.now()
            
            # 1. Schaut zuerst, ob im Service-Aufruf Werte mitgegeben wurden
            # 2. Wenn nicht, nimmt er die Werte, die aktuell in den UI-Steuerelementen (data) stehen
            flour = call.data.get(ATTR_FLOUR, data.get("last_flour_g", 50))
            water = call.data.get(ATTR_WATER, data.get("last_water_g", 50))
            starter = call.data.get(ATTR_STARTER, data.get("last_starter_g", 10))
            
            data["state"] = "running"
            data["last_fed"] = now.isoformat()
            data["expires_at"] = (now + datetime.timedelta(hours=data["interval"])).isoformat()
            data["remaining_seconds"] = data["interval"] * 3600
            
            data["last_flour_g"] = flour
            data["last_water_g"] = water
            data["last_starter_g"] = starter
            data["total_mass_g"] = flour + water + starter
            
            async_dispatcher_send(hass, f"{DOMAIN}_{entry_id}_updated")
            
    async def handle_pause(call: ServiceCall):
        for entry_id in get_target_entries(call):
            data = hass.data[DOMAIN][entry_id]
            if data["state"] == "paused": continue
            now = dt_util.now()
            expires = dt_util.parse_datetime(data["expires_at"])
            if expires:
                data["state"] = "paused"
                data["remaining_seconds"] = max(0, (expires - now).total_seconds())
            async_dispatcher_send(hass, f"{DOMAIN}_{entry_id}_updated")

    async def handle_resume(call: ServiceCall):
        for entry_id in get_target_entries(call):
            data = hass.data[DOMAIN][entry_id]
            if data["state"] == "running": continue
            now = dt_util.now()
            new_expires = now + datetime.timedelta(seconds=data["remaining_seconds"])
            data["state"] = "running"
            data["expires_at"] = new_expires.isoformat()
            data["last_fed"] = (new_expires - datetime.timedelta(hours=data["interval"])).isoformat()
            async_dispatcher_send(hass, f"{DOMAIN}_{entry_id}_updated")

    # Hier übergeben wir das neue Schema mit den Zutaten an den Fütterungs-Service
    hass.services.async_register(DOMAIN, "feed", handle_feed, schema=SERVICE_FEED_SCHEMA)
    hass.services.async_register(DOMAIN, "pause", handle_pause, schema=SERVICE_BASE_SCHEMA)
    hass.services.async_register(DOMAIN, "resume", handle_resume, schema=SERVICE_BASE_SCHEMA)
