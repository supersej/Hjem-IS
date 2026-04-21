import logging
import aiohttp
import async_timeout
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hjem-is"

async def async_setup_entry(hass, entry, async_add_entities):
    lat = entry.data["latitude"]
    lng = entry.data["longitude"]
    selected_id = entry.data.get("selected_stop_id")
    
    coordinator = HjemIsCoordinator(hass, lat, lng)
    await coordinator.async_config_entry_first_refresh()

    entities = []
    
    if selected_id == "all":
        if coordinator.data:
            for stop in coordinator.data:
                raw_address = stop.get("address", "Ukendt")
                clean_address = raw_address.split(',')[0]
                stop_id = int(stop["id"])
                entities.append(
                    HjemIsSensor(coordinator, stop_id, clean_address, entry.entry_id)
                )
    else:
        address_name = entry.data.get("stop_address", f"Stop {selected_id}")
        entities.append(
            HjemIsSensor(coordinator, int(selected_id), address_name, entry.entry_id)
        )

    async_add_entities(entities)


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
                    data = await response.json()
                    self._adjust_interval(data)
                    return data

    def _adjust_interval(self, data):
        if not data:
            return
        next_visit_str = data[0].get("arrival_date")
        if next_visit_str:
            today_str = datetime.now().date().isoformat()
            if next_visit_str == today_str:
                if self.update_interval != timedelta(minutes=15):
                    _LOGGER.info("Hjem-IS kommer i dag! Opdateringsinterval: 15 min.")
                    self.update_interval = timedelta(minutes=15)
            else:
                if self.update_interval != timedelta(hours=6):
                    _LOGGER.info("Hjem-IS kommer ikke i dag. Opdateringsinterval: 6 timer.")
                    self.update_interval = timedelta(hours=6)


class HjemIsSensor(SensorEntity):
    _attr_icon = "mdi:ice-cream-truck"
    _attr_has_entity_name = False

    def __init__(self, coordinator, my_stop_id, address_name, entry_id):
        self.coordinator = coordinator
        self.my_stop_id = my_stop_id
        self._attr_unique_id = f"hjem_is_{entry_id}_{my_stop_id}"
        self._attr_name = f"Hjem-IS {address_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Hjem-IS",
            manufacturer="Hjem-IS",
            model="Isrute",
        )

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def _get_my_stop_data(self):
        data = self.coordinator.data
        if not data:
            return None
        for stop in data:
            if int(stop.get("id", -1)) == self.my_stop_id:
                return stop
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
        stop = self._get_my_stop_data
        return stop if stop else {}