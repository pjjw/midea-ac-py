import voluptuous as vol
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity import Entity


try:
    from homeassistant.components.sensor import SensorEntity
except ImportError:
    class SensorEntity(Entity):
        """Base class for sensor entities."""

try:
    from homeassistant.components.sensor import STATE_CLASSES
except ImportError:
    STATE_CLASSES = []


CONF_TYPE = 'type'
CONF_HOST = 'host'
CONF_ID = 'id'
CONF_TOKEN = 'token'
CONF_K1 = 'k1'
CONF_PORT = 'port'

SCAN_INTERVAL = timedelta(seconds=15)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_ID): cv.string,
    vol.Optional(CONF_TOKEN, default=""): cv.string,
    vol.Optional(CONF_K1, default=""): cv.string,
    vol.Optional(CONF_PORT, default=6444): vol.Coerce(int),
    vol.Optional(CONF_TYPE, default=0xdb): vol.Coerce(int),
})

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the Midea lan service and query appliances."""

    from msmart.device import front_load_washer as db

    device_ip = config.get(CONF_HOST)
    device_id = config.get(CONF_ID)
    device_token = config.get(CONF_TOKEN)
    device_k1 = config.get(CONF_K1)
    device_port = config.get(CONF_PORT)

    device = db(device_ip, int(device_id), device_port)
    device._type = config.get(CONF_TYPE)
    if device_token and device_k1:
        # device.authenticate(device_k1, device_token)
        device._protocol_version = 3
        device._token = bytearray.fromhex(device_token)
        device._key = bytearray.fromhex(device_k1)
        device._lan_service._token = device._token
        device._lan_service._key = device._key
        

    entities = []
    entities.append(MideaWasherDevice(
            hass, device))

    async_add_entities(entities)

class MideaWasherDevice(SensorEntity, RestoreEntity):

    def __init__(self, hass, device):
        """Initialize the washer device."""

        self._device = device

        self.hass = hass
        self._old_state = None
        self._changed = False
    
    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        self._old_state = await self.async_get_last_state()
    
    async def async_update(self):
        """Update the state."""
        await self.hass.async_add_executor_job(self._device.refresh)
    
    @property
    def name(self):
        """Return the name of the device."""
        return "midea_{:2x}_{}".format(self._device._type, self._device.id)

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return 'mdi:washing-machine'

    @property
    def native_value(self):
        """Return state of the sensor."""
        return self._device.machine_status.name

    @property
    def available(self):
        """Checks if is available."""
        return self._device.online
    
    @property
    def extra_state_attributes(self):
        """Return the optional state attributes."""

        data = {
            'power': self._device.power,
            'machine_status': self._device.machine_status.name,
            'work_mode': self._device.work_mode,
            'cycle_program': self._device.cycle_program.name,
            'water_line': self._device.water_line,
            'dring_state ': self._device.dring_state,
            'remainder_time': self._device.remainder_time,
        # self._machine_status = front_load_washer.machine_status_enum.UNKNOWN
        # self._work_mode = False
        # self._cycle_program = front_load_washer.cycle_program_enum.UNKNOWN
        # self._water_line = 0
        # self._dring_state = 0
        # self._rinse_times = 0
        # self._temperature = 0
        # self._dehydrate_speed = 0
        # self._wash_times = 0
        # self._dehydrate_time = 0
        # self._wash_dose = 0
        # self._memory = 0
        # self._supple_dose  = 0
        # self._remainder_time = 0
        # self._appliance_type = 0xff
        }

        return data