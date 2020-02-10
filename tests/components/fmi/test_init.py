"""Test init of FMI integration."""
from datetime import datetime

from asynctest import Mock, patch

from homeassistant.components.fmi.const import DOMAIN
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers import entity_registry
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_migration(hass):
    """Test that we can migrate FMI to stable unique ID."""
    home_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Home",
        data={CONF_NAME: "Test Home", CONF_LATITUDE: 62.4, CONF_LONGITUDE: 25.67},
    )
    home_entry.add_to_hass(hass)
    with patch(
        "fmi_weather_client.weather_by_coordinates",
        return_value=Mock(
            place="Porvoo",
            lat=62.4,
            lon=25.67,
            data=Mock(
                time=datetime.now(),
                temperature=Mock(value=1.2, unit="°C"),
                pressure=Mock(value=1010.7, unit="hPa"),
                humidity=Mock(value=91.0, unit="%"),
                wind_speed=Mock(value=2.0, unit="m/s"),
                wind_direction=Mock(value=101.0, unit="°"),
                symbol=Mock(value=1.0, unit=""),
            ),
        ),
    ) as mock_weather, patch(
        "fmi_weather_client.forecast_by_coordinates",
        return_value=Mock(place="Porvoo", lat=62.4, lon=25.67, forecasts=[]),
    ) as mock_forecast:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    ent_reg = await entity_registry.async_get_registry(hass)

    weather_home = ent_reg.async_get("weather.test_home")
    assert weather_home.unique_id == "62.4, 25.67"

    assert hass.states.get("weather.test_home").state == "sunny"
    assert hass.states.get("weather.test_home").attributes.get("temperature") == 1.2
    assert hass.states.get("weather.test_home").attributes.get("pressure") == 1010.7
    assert hass.states.get("weather.test_home").attributes.get("humidity") == 91.0
    assert (
        hass.states.get("weather.test_home").attributes.get("wind_speed") == 2.0 * 3.6
    )
    assert hass.states.get("weather.test_home").attributes.get("wind_bearing") == 101.0
    assert hass.states.get("weather.test_home").attributes.get("symbol") == 1.0

    assert len(mock_weather.mock_calls) == 1
    assert len(mock_forecast.mock_calls) == 1
