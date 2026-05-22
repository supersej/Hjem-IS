from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta
import logging
import aiohttp
import async_timeout
from homeassistant.helpers.update_coordinator import UpdateFailed
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hjem_is"
PLATFORMS = ["sensor", "binary_sensor"]

TURBO_INTERVAL = timedelta(minutes=15)
NORMAL_INTERVAL = timedelta(hours=6)


def _is_today(date_str: str | None) -> bool:
    """Returner True hvis date_str (ISO-format) er dagens dato."""
    if not date_str:
        return False
    return date_str == datetime.now().date().isoformat()


class HjemIsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, lat, lng):
        super().__init__(
            hass,
            _LOGGER,
            name="Hjem-IS API",
            update_interval=NORMAL_INTERVAL,
        )
        self.lat = lat
        self.lng = lng
        self.turbo_active = False

    async def _async_update_data(self):
        url = (
            f"https://sms.hjem-is.dk/"
            f"?coordinates[lat]={self.lat}&coordinates[lng]={self.lng}&format=json"
        )
        async with async_timeout.timeout(10):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Fejl ved hentning: {response.status}")
                    data = await response.json()
                    self._adjust_interval(data)
                    return data

    def _adjust_interval(self, data):
        """Skifter mellem turbo (15 min) og normal (6 timer) opdateringsinterval.

        Kalder async_set_update_interval() frem for direkte assignment på
        self.update_interval — det direkte assignment ændrer kun attributten,
        men genplanlægger ikke den allerede-kørende HA-timer.
        """
        if not data:
            return
        next_visit_str = data[0].get("arrival_date")
        should_be_turbo = _is_today(next_visit_str)

        if should_be_turbo and not self.turbo_active:
            _LOGGER.info("Hjem-IS kommer i dag! Skifter til turbo-interval: 15 min.")
            self.turbo_active = True
            self.async_set_update_interval(TURBO_INTERVAL)
        elif not should_be_turbo and self.turbo_active:
            _LOGGER.info("Hjem-IS kommer ikke i dag. Skifter til normalt interval: 6 timer.")
            self.turbo_active = False
            self.async_set_update_interval(NORMAL_INTERVAL)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    lat = entry.data["latitude"]
    lng = entry.data["longitude"]

    coordinator = HjemIsCoordinator(hass, lat, lng)
    await coordinator.async_config_entry_first_refresh()

    # Gem coordinator i hass.data så sensor.py og binary_sensor.py kan hente den
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok