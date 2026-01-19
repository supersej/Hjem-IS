import logging
import aiohttp
import async_timeout
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hjem_is"

async def async_setup_entry(hass, entry, async_add_entities):
    lat = entry.data["latitude"]
    lng = entry.data["longitude"]
    selected_id = entry.data.get("selected_stop_id")
    address_name = entry.data.get("stop_address", f"Stop {selected_id}")

    coordinator = HjemIsCoordinator(hass, lat, lng)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([HjemIsSensor(coordinator, selected_id, address_name)])

class HjemIsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, lat, lng):
        super().__init__(
            hass,
            _LOGGER,
            name="Hjem-IS API",
            update_interval=timedelta(hours=6),
        )
        self.lat = lat
        self.lng = lng

    async def _async_update_data(self):
        url = f"https://sms.hjem-is.dk/?coordinates[lat]={self.lat}&coordinates[lng]={self.lng}&format=json"
        async with async_timeout.timeout(10):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Fejl ved hentning: {response.status}")
                    return await response.json()

class HjemIsSensor(SensorEntity):
    _attr_icon = "mdi:ice-cream-truck"
    _attr_has_entity_name = False

    def __init__(self, coordinator, selected_id, address_name):
        self.coordinator = coordinator
        self.selected_id = selected_id
        self._attr_unique_id = f"hjem_is_stop_{selected_id}"
        self._attr_name = f"Hjem-IS {address_name}"

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def _get_my_stop_data(self):
        """Hjælpefunktion til at finde KUN dette stops data"""
        data = self.coordinator.data
        if not data: return None
        
        # Find stop med matchende ID
        if self.selected_id:
            for stop in data:
                if stop.get("id") == self.selected_id:
                    return stop
        
        # Fallback til første stop
        if len(data) > 0:
            return data[0]
        return None

    @property
    def state(self):
        stop = self._get_my_stop_data
        if stop:
            events = stop.get("upcoming_plan_events_dates", [])
            if events:
                return events[0].get("date")
        return "Ukendt"

    @property
    def extra_state_attributes(self):
        # NU returnerer vi kun data for det specifikke stop!
        stop = self._get_my_stop_data
        if stop:
            return stop # Dumper hele objektet for dette stop (adresse, koordinater, sms_text osv.)
        return {}

    async def async_update(self):
        await self.coordinator.async_request_refresh()