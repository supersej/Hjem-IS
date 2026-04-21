import voluptuous as vol
import aiohttp
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

DOMAIN = "hjem_is"

class HjemIsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        self.coords = {}
        self.available_stops = {}
        self.stop_details = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.coords = user_input
            try:
                stops = await self._get_stops(user_input["latitude"], user_input["longitude"])
                if not stops:
                    errors["base"] = "no_stops_found"
                else:
                    stops.sort(key=lambda x: x["address"])
                    
                    # 1. Tilføj muligheden for at vælge ALLE
                    self.available_stops = {
                        "all": "🌟 Hent ALLE stop på ruten (Opretter sensor for hver)"
                    }
                    
                    # 2. Tilføj de enkelte stop som før
                    for stop in stops:
                        stop_id = str(stop["id"])
                        self.available_stops[stop_id] = f"{stop['address']} ({stop['google_estimate_time'][11:16]})"
                        # Gem vejnavn til sensor-navngivning
                        self.stop_details[stop_id] = stop['address'].split(',')[0]
                        
                    return await self.async_step_pick_stop()
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("latitude", default=self.hass.config.latitude): cv.latitude,
                vol.Required("longitude", default=self.hass.config.longitude): cv.longitude,
            }),
            errors=errors
        )

    async def async_step_pick_stop(self, user_input=None):
        if user_input is not None:
            stop_id = user_input["stop_id"]
            
            # Bestem titel og data baseret på valg
            if stop_id == "all":
                title = "Hjem-IS (Hele ruten)"
                stop_address = "Alle"
            else:
                stop_address = self.stop_details[stop_id]
                title = f"Hjem-IS ({stop_address})"

            user_selection = {
                **self.coords,
                "selected_stop_id": stop_id, # Her gemmes enten et ID eller "all"
                "stop_address": stop_address
            }
            return self.async_create_entry(title=title, data=user_selection)

        return self.async_show_form(
            step_id="pick_stop",
            data_schema=vol.Schema({
                vol.Required("stop_id"): vol.In(self.available_stops)
            })
        )

    async def _get_stops(self, lat, lng):
        url = f"https://sms.hjem-is.dk/?coordinates[lat]={lat}&coordinates[lng]={lng}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        return []