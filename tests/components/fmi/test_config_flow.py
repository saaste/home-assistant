"""Test the FMI config flow."""
from asynctest import patch

from homeassistant import config_entries, setup
from homeassistant.components.fmi.const import DOMAIN
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch("fmi_weather_client.weather_by_coordinates", return_value={},), patch(
        "homeassistant.components.fmi.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.fmi.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Home", CONF_LATITUDE: 60.4000, CONF_LONGITUDE: 25.6738},
        )
    assert result2["type"] == "create_entry"
    assert result2["title"] == "Home"
    assert result2["data"] == {
        CONF_NAME: "Home",
        CONF_LATITUDE: 60.4000,
        CONF_LONGITUDE: 25.6738,
    }
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1
