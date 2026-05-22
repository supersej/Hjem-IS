import logging
from datetime import datetime
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hjem_is"


def _is_today(date_str: str | None) -> bool:
    """Returner True hvis date_str (ISO-format) er dagens dato."""
    if not date_str:
        return False
    return date_str == datetime.now().date().isoformat()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HjemIsTurboSensor(coordinator, entry.entry_id)])


class HjemIsTurboSensor(CoordinatorEntity, BinarySensorEntity):
    """Binær sensor: True når koordinatoren kører turbo-opdatering (leveringsdag).

    Arver fra CoordinatorEntity så HA automatisk kalder async_write_ha_state()
    hver gang coordinatoren henter nye data — ingen manuel async_update nødvendig.
    """

    _attr_icon = "mdi:speedometer"
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._attr_unique_id = f"hjem_is_{entry_id}_turbo"
        self._attr_name = "Hjem-IS Turbo Mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Hjem-IS",
            manufacturer="Hjem-IS",
            model="Isrute",
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.turbo_active

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        next_visit = data[0].get("arrival_date") if data else None
        return {
            "next_visit_date": next_visit,
            "update_interval_minutes": int(
                self.coordinator.update_interval.total_seconds() / 60
            ),
            "is_delivery_day": _is_today(next_visit),
        }