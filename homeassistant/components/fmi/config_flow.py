"""Config flow to configure FMI component."""

from typing import Any, Dict

import fmi_weather_client as fmi
from fmi_weather_client.errors import ClientError, ServerError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify

from .const import DEFAULT_NAME, DOMAIN


class FMIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for FMI component."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize FMI configuration flow."""
        self._errors: Dict[str, str] = {}

    async def async_step_user(self, user_input=None) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        name = DEFAULT_NAME
        latitude = self.hass.config.latitude
        longitude = self.hass.config.longitude

        if user_input is not None:
            is_name_valid = self.is_name_available(user_input.get(CONF_NAME))
            is_location_valid = await self.async_is_valid_location(
                user_input.get(CONF_LATITUDE), user_input.get(CONF_LONGITUDE)
            )

            if is_name_valid and is_location_valid:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME), data=user_input
                )

            # Overwrite default values is user filled the form
            name = user_input.get(CONF_NAME)
            latitude = user_input.get(CONF_LATITUDE)
            longitude = user_input.get(CONF_LONGITUDE)

            if not is_name_valid:
                self._errors[CONF_NAME] = "name_exists"
            if not is_location_valid:
                self._errors["base"] = "invalid_location"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=name): str,
                    vol.Required(CONF_LATITUDE, default=latitude): cv.latitude,
                    vol.Required(CONF_LONGITUDE, default=longitude): cv.longitude,
                }
            ),
            errors=self._errors,
        )

    def is_name_available(self, name) -> bool:
        """Return true if location name is available."""
        name = slugify(name)
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            entry_name = slugify(entry.title)
            if entry_name == name:
                return False
        return True

    async def async_is_valid_location(self, latitude: str, longitude: str) -> bool:
        """Return true if location has weather available."""
        try:
            lat = float(latitude)
            lon = float(longitude)
            await fmi.async_weather_by_coordinates(lat, lon)
            return True
        except (ClientError, ServerError):
            return False
