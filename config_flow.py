import voluptuous as vol
import aiohttp
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

DOMAIN = "hjem_is"

class HjemIsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        self.coords = {}
        self.available_stops = {} # ID -> "Adresse (Tid)"
        self.stop_details = {}    # ID -> "Ren Adresse"

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.coords = user_input
            try:
                stops = await self._get_stops(user_input["latitude"], user_input["longitude"])
                if not stops:
                    errors["base"] = "no_stops_found"
                else:
                    # Sorterer listen alfabetisk på adressenavn
                    stops.sort(key=lambda x: x["address"])
                    
                    # Gemmer data til dropdown
                    self.available_stops = {
                        str(stop["id"]): f"{stop['address']} ({stop['google_estimate_time'][11:16]})"
                        for stop in stops
                    }
                    # Gemmer rent vejnavn til senere brug
                    self.stop_details = {
                        str(stop["id"]): stop['address'].split(',')[0] # F.eks "Musvågevej 3"
                        for stop in stops
                    }
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
            # Vi gemmer den rene adresse med, så sensoren kan hedde det
            user_selection = {
                **self.coords,
                "selected_stop_id": int(stop_id),
                "stop_address": self.stop_details[stop_id]
            }
            # Titlen på integrationen i listen
            title = f"Hjem-IS ({self.stop_details[stop_id]})"
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