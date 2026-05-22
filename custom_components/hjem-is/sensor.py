import logging
import re
import aiohttp
import async_timeout
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hjem_is"

TURBO_INTERVAL = timedelta(minutes=15)
NORMAL_INTERVAL = timedelta(hours=6)


def _slugify(text: str) -> str:
    """Lav en stabil slug af en adresse til brug i unique_id.

    Eksempel: "Hovedgaden 2"   -> "hovedgaden_2"
              "Øster Allé 14"  -> "oester_alle_14"

    Stabil på tværs af API-opdateringer: det fysiske vejnavn ændrer sig
    ikke selvom API'ens interne stop-ID gør det.
    """
    text = text.lower().strip()
    text = re.sub(r"æ", "ae", text)
    text = re.sub(r"ø", "oe", text)
    text = re.sub(r"å", "aa", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _is_today(date_str: str | None) -> bool:
    """Returner True hvis date_str (ISO-format) er dagens dato."""
    if not date_str:
        return False
    return date_str == datetime.now().date().isoformat()


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
                entities.append(HjemIsSensor(coordinator, stop_id, clean_address, entry.entry_id))

        # Én turbo-sensor pr. config entry (dækker hele ruten)
        entities.append(HjemIsTurboSensor(coordinator, entry.entry_id))
    else:
        address_name = entry.data.get("stop_address", f"Stop {selected_id}")
        entities.append(HjemIsSensor(coordinator, int(selected_id), address_name, entry.entry_id))
        entities.append(HjemIsTurboSensor(coordinator, entry.entry_id))

    async_add_entities(entities)


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
        self.turbo_active = False  # eksponeret til HjemIsTurboSensor

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

        VIGTIGT: Vi kalder async_set_update_interval() i stedet for at sætte
        self.update_interval direkte. Det direkte assignment ændrer kun
        attributten, men den allerede-planlagte HA-timer kører stadig på
        det gamle interval. async_set_update_interval() annullerer og
        genplanlægger timeren korrekt.
        """
        if not data:
            return

        # Brug arrival_date fra første stop — hele ruten kører samme dag
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


class HjemIsSensor(SensorEntity):
    _attr_icon = "mdi:ice-cream-truck"
    _attr_has_entity_name = False

    def __init__(self, coordinator, initial_stop_id: int, address_name: str, entry_id: str):
        self.coordinator = coordinator
        self.initial_stop_id = initial_stop_id
        self.address_name = address_name

        # Stabil unique_id: entry_id (HA's interne UUID) + adresse-slug.
        # IKKE stop["id"] fra API'en — den ændres ved sæsonskift og skaber dubletter.
        self._attr_unique_id = f"hjem_is_{entry_id}_{_slugify(address_name)}"
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
        # Primær match: adresse-prefix — overlever API's ID-rotation.
        # API returnerer fx "Hovedgaden 2, 2800 Kongens Lyngby";
        # vi sammenligner kun vejnavnet (split på første komma).
        for stop in data:
            if stop.get("address", "").split(',')[0] == self.address_name:
                return stop
        # Fallback: original stop-ID fra da sensoren blev oprettet.
        for stop in data:
            if int(stop.get("id", -1)) == self.initial_stop_id:
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


class HjemIsTurboSensor(BinarySensorEntity):
    """Binær sensor: True når koordinatoren kører turbo-opdatering (leveringsdag)."""

    _attr_icon = "mdi:speedometer"
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, entry_id: str):
        self.coordinator = coordinator
        self._attr_unique_id = f"hjem_is_{entry_id}_turbo"
        self._attr_name = "Hjem-IS Turbo Mode"
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
    def is_on(self) -> bool:
        return self.coordinator.turbo_active

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        next_visit = None
        if data:
            next_visit = data[0].get("arrival_date")
        return {
            "next_visit_date": next_visit,
            "update_interval_minutes": int(
                self.coordinator.update_interval.total_seconds() / 60
            ),
            "is_delivery_day": _is_today(next_visit),
        }