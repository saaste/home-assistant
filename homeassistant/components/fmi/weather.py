"""Support for Finnish Meteorological Institute (FMI) weather service."""
from datetime import timedelta
import logging
from typing import Any, Dict, List, Optional

import fmi_weather_client as fmi
import fmi_weather_client.errors as fmi_errors
from fmi_weather_client.models import Forecast, Weather

from homeassistant.components.weather import WeatherEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME, TEMP_CELSIUS
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, config: ConfigEntry, async_add_entities
):
    """Add a weather entity from a config_entry."""
    lat = config.data[CONF_LATITUDE]
    lon = config.data[CONF_LONGITUDE]

    class FMIResponse:
        """FMI response."""

        def __init__(self, weather: Weather, forecast: Forecast):
            """Initialize FMI Response."""
            self.weather: Weather = weather
            self.forecast: Forecast = forecast

    async def async_update_data():
        """Fetch data from FMI."""
        try:
            weather = await fmi.async_weather_by_coordinates(lat, lon)
            forecast = await fmi.async_forecast_by_coordinates(lat, lon, 8)
            return FMIResponse(weather, forecast)
            # return {"weather": weather, "forecast": forecast}
        except fmi_errors.ClientError as err:
            _LOGGER.warning(
                "Unable to fetch data from FMI: Client Error. Status: %d. Message: %s",
                err.status_code,
                err.message,
            )
            raise UpdateFailed
        except fmi_errors.ServerError as err:
            _LOGGER.warning(
                "Unable to fetch data from FMI: Server Error. Status: %d. Message: %s",
                err.status_code,
                err.body,
            )
            raise UpdateFailed

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="FMI weather",
        update_method=async_update_data,
        update_interval=timedelta(minutes=20),
    )

    await coordinator.async_refresh()
    async_add_entities([FMIWeather(config, coordinator, lat, lon)])


class FMIWeather(WeatherEntity):
    """Implementation of a FMI weather condition."""

    def __init__(
        self,
        config: ConfigEntry,
        coordinator: DataUpdateCoordinator,
        latitude: float,
        longitude: float,
    ):
        """Initialize FMIWeather."""
        self._config: ConfigEntry = config
        self._coordinator: DataUpdateCoordinator = coordinator
        self._latitude: float = latitude
        self._longitude: float = longitude

    @property
    def unique_id(self) -> str:
        """Return a unique id."""
        return f"{self._latitude}, {self._longitude}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        name = self._config.data[CONF_NAME]

        if name is not None:
            return name

        return DEFAULT_NAME

    @property
    def temperature(self) -> Optional[float]:
        """Return the temperature."""
        if self._coordinator.data.weather.data.temperature is not None:
            return self._coordinator.data.weather.data.temperature.value
        return None

    @property
    def temperature_unit(self) -> str:
        """Return the temperature unit."""
        return TEMP_CELSIUS

    @property
    def pressure(self) -> Optional[float]:
        """Return the pressure."""
        if self._coordinator.data.weather.data.pressure is not None:
            return self._coordinator.data.weather.data.pressure.value
        return None

    @property
    def humidity(self) -> Optional[float]:
        """Return the humidity."""
        if self._coordinator.data.weather.data.humidity is not None:
            return self._coordinator.data.weather.data.humidity.value
        return None

    @property
    def wind_speed(self) -> Optional[float]:
        """Return the wind speed."""
        if self._coordinator.data.weather.data.wind_speed is not None:
            return round(self._coordinator.data.weather.data.wind_speed.value * 3.6, 1)
        return None

    @property
    def wind_bearing(self) -> Optional[float]:
        """Return the wind bearing."""
        if self._coordinator.data.weather.data.wind_direction is not None:
            return self._coordinator.data.weather.data.wind_direction.value
        return None

    @property
    def attribution(self) -> str:
        """Return the attribution."""
        return "Finnish Meteorological Institute (FMI)"

    @property
    def condition(self) -> Optional[str]:
        """Return the weather condition."""
        if self._coordinator.data.weather.data.symbol is not None:
            return _symbol_to_condition(
                self._coordinator.data.weather.data.symbol.value
            )
        return None

    @property
    def forecast(self) -> Optional[List[Dict[str, Any]]]:
        """Weather forecast."""
        if self._coordinator.data.forecast.forecasts is not None:
            forecasts = []
            for forecast in self._coordinator.data.forecast.forecasts:
                fcast = {
                    "datetime": forecast.time.isoformat("T"),
                    "temperature": forecast.temperature.value,
                    "condition": _symbol_to_condition(forecast.symbol.value),
                }
                forecasts.append(fcast)
            return forecasts
        return None

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success

    @property
    def device_state_attributes(self) -> Optional[Dict]:
        """Return FMI specific attributes."""
        if self._coordinator.data.weather is None:
            return None

        attributes = {}
        weather_data = self._coordinator.data.weather.data

        if weather_data.wind_u_component is not None:
            attributes["wind_u_component"] = weather_data.wind_u_component.value
        if weather_data.wind_v_component is not None:
            attributes["wind_v_component"] = weather_data.wind_v_component.value
        if weather_data.wind_max is not None:
            attributes["wind_max"] = weather_data.wind_max.value
        if weather_data.wind_gust is not None:
            attributes["wind_gust"] = weather_data.wind_gust.value
        if weather_data.symbol is not None:
            attributes["symbol"] = weather_data.symbol.value
        if weather_data.cloud_cover is not None:
            attributes["cloud_cover"] = weather_data.cloud_cover.value
        if weather_data.cloud_low_cover is not None:
            attributes["cloud_low_cover"] = weather_data.cloud_low_cover.value
        if weather_data.cloud_mid_cover is not None:
            attributes["cloud_mid_cover"] = weather_data.cloud_mid_cover.value
        if weather_data.cloud_high_cover is not None:
            attributes["cloud_high_cover"] = weather_data.cloud_high_cover.value
        if weather_data.radiation_short_wave_acc is not None:
            attributes[
                "radiation_short_wave_acc"
            ] = weather_data.radiation_short_wave_acc.value
        if weather_data.radiation_short_wave_acc is not None:
            attributes[
                "radiation_short_wave_surface_net_acc"
            ] = weather_data.radiation_short_wave_surface_net_acc.value
        if weather_data.radiation_long_wave_acc is not None:
            attributes[
                "radiation_long_wave_acc"
            ] = weather_data.radiation_long_wave_acc.value
        if weather_data.radiation_long_wave_surface_net_acc is not None:
            attributes[
                "radiation_long_wave_surface_net_acc"
            ] = weather_data.radiation_long_wave_surface_net_acc.value
        if weather_data.radiation_short_wave_diff_surface_acc is not None:
            attributes[
                "radiation_short_wave_diff_surface_acc"
            ] = weather_data.radiation_short_wave_diff_surface_acc.value
        if weather_data.geopotential_height is not None:
            attributes["geopotential_height"] = weather_data.geopotential_height.value
        if weather_data.land_sea_mask is not None:
            attributes["land_sea_mask"] = weather_data.land_sea_mask.value

        return attributes

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)

    async def async_update(self):
        """Update the entity. Only used by the generic entity update service."""
        await self._coordinator.async_request_refresh()


def _symbol_to_condition(symbol: float) -> Optional[str]:
    """Get condition based on symbol."""
    if symbol is not None:
        if symbol in [1]:
            return "sunny"
        if symbol in [91, 92]:
            return "fog"
        if symbol in [21, 22, 31, 32]:
            return "rainy"
        if symbol in [23, 33]:
            return "pouring"
        if symbol in [71, 72, 73, 81, 82, 83]:
            return "snowy-rainy"
        if symbol in [41, 42, 43, 51, 52, 53]:
            return "snowy"
        if symbol in [61, 62, 63, 64]:
            return "lightning"
        if symbol in [2]:
            return "partlycloudy"
        if symbol in [3]:
            return "cloudy"

    return None
