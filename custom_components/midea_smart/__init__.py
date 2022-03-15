"""Support for Midea Smart."""
import logging
_LOGGER = logging.getLogger(__name__)
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from msmart.device import(
    air_conditioning as ac,
    front_load_washer as db,
)
import msmart.device as Device

from .const import (
    CONF_ID,
    DOMAIN,
    CONF_TOKEN,
    CONF_HOST,
    KEY_COORDINATOR,
    KEY_CONSTRUCTOR,
    KEY_PLATFORMS,
    KEY_ENTITIES,
    KEY_DEVICE,
    KEY_TYPE,
    CONF_TYPE,
    SCAN_INTERVAL,
)

MIDEA_CONFIG = {
    0xAC: {
        "constructor": ac,
        "platforms": [CLIMATE_DOMAIN, SWITCH_DOMAIN, SENSOR_DOMAIN],
        "entities": {
            "default": {
                "type": "climate",
                "icon": "hass:air-conditioner",
            },
            "beeper": {
                "type": "switch",
                "icon": "hass:bell",
                "property": "prompt_tone",
            }
        },
    },
    0xDB: {
        "constructor": db,
        "platforms": [SENSOR_DOMAIN],
        "entities": {
            "default": {
                "type": "sensor",
                "icon": "hass:washing-machine",
            },
        }
    }
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the Midea Smart components from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("entry.data: {}".format(entry.data))

    return await async_setup_device_entry(hass, entry)



@callback
def get_midea_config(device_type, config_key):
    """Return the Midea config for a key."""
    config = MIDEA_CONFIG.get(device_type)
    if config is None:
        return None
    return config.get(config_key)

async def async_create_midea_device_and_coordinator(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up a data coordinator and one midea smart device to service multiple entities."""
    _config = config_entry.data
    _type = _config[CONF_TYPE]
    _host = _config[CONF_HOST]
    _id = _config[CONF_ID]


    constructor = get_midea_config(_type, KEY_CONSTRUCTOR)
    if constructor is not None:
        platform_device = constructor(_host, int(_id), 6444)
        platform_device.set_device_detail(_config)
    else:
        _LOGGER.error("Unsupported device found: %s", _type)
        return

    # Create update midea device and coordinator
    coordinator = MideaCoordinator(hass, platform_device)

    hass.data[DOMAIN][config_entry.entry_id] = {
        KEY_DEVICE: platform_device,
        KEY_COORDINATOR: coordinator,
        KEY_TYPE: type
    }


async def async_setup_device_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the Midea Smart device component from a config entry."""
    _LOGGER.debug("async_setup_device_entry: {}".format(config_entry.data))
    config_type = config_entry.data[CONF_TYPE]
    platforms = get_midea_config(config_type, KEY_PLATFORMS)
    await async_create_midea_device_and_coordinator(hass, config_entry)

    if not platforms:
        return False
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    hass.config_entries.async_setup_platforms(config_entry, platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("async_setup_device_entry: {}".format(config_entry))
    config_type = config_entry.data[CONF_TYPE]
    platforms = get_midea_config(config_type, KEY_PLATFORMS)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, platforms
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)



class MideaCoordinator(DataUpdateCoordinator):
    """Manages polling for state changes from the device."""

    def __init__(self, hass: HomeAssistant, device: Device) -> None:
        """Initialize the data update coordinator."""
        DataUpdateCoordinator.__init__(
            self,
            hass,
            _LOGGER,
            name=device.name,
            update_interval=SCAN_INTERVAL,
        )
        self._device = device

    async def _async_update_data(self):
        """Update the state of the device."""
        _LOGGER.debug("Update the state of the device")
        async with async_timeout.timeout(10):
            await self.hass.async_add_executor_job(self._device.refresh)

    async def apply_changes(self):
        """Apply changes to the device. """
        async with async_timeout.timeout(10):
            await self.hass.async_add_executor_job(self._device.apply)

class MideaEntity(CoordinatorEntity):
    """Base class for Midea entities."""

    def __init__(self, coordinator: MideaCoordinator, desc: str=None):
        """Initialize the entity."""
        _LOGGER.debug("coordinator {}".format(coordinator))
        super().__init__(coordinator)
        self._desc = desc
        self._device = coordinator._device
        self._type = self._device.type
        self._device.unique_id = self._device.name
        self._coordinator = coordinator
        self._config = MIDEA_CONFIG[self._type][KEY_ENTITIES][desc]

    @property
    def unique_id(self):
        """Return a unique id for the device."""
        if self._desc == "default":
            return self._device.name
        return "{}_{}".format(self._device.name, self._desc)

    @property
    def name(self):
        """Return the name of the device."""
        if self._desc == "default":
            return self._device.name
        return "{}_{}".format(self._device.name, self._desc)
    
    @property
    def icon(self):
        """Return the icon for the device."""
        return self._config.get("icon", "mdi:home-assistant")

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "name": self._device.name,
            "identifiers": {(DOMAIN, self._device.unique_id)},
            "manufacturer": "Midea",
            "model": "0x{:2X}".format(self._device.type),
            "host": self._device.ip,
            "sw_version": self._device._protocol_version,
            # "ssid": self._device.ssid,
            # "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
        }



