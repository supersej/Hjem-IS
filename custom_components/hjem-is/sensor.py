import logging
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hjem_is"


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


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    selected_id = entry.data.get("selected_stop_id")

    entities = []

    if selected_id == "all":
        if coordinator.data:
            for stop in coordinator.data:
                raw_address = stop.get("address", "Ukendt")
                clean_address = raw_address.split(',')[0]
                stop_id = int(stop["id"])
                entities.append(HjemIsSensor(coordinator, stop_id, clean_address, entry.entry_id))
    else:
        address_name = entry.data.get("stop_address", f"Stop {selected_id}")
        entities.append(HjemIsSensor(coordinator, int(selected_id), address_name, entry.entry_id))

    async_add_entities(entities)


class HjemIsSensor(CoordinatorEntity, SensorEntity):
    """Sensor der viser næste besøgsdato for et Hjem-IS stop.

    Arver fra CoordinatorEntity så HA automatisk kalder async_write_ha_state()
    hver gang coordinatoren henter nye data — ingen manuel async_update nødvendig.
    """

    _attr_icon = "mdi:ice-cream-truck"
    _attr_has_entity_name = False

    def __init__(self, coordinator, initial_stop_id: int, address_name: str, entry_id: str):
        super().__init__(coordinator)
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