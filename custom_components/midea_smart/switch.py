
import logging
_LOGGER = logging.getLogger(__name__)

from homeassistant.components.switch import DEVICE_CLASS_SWITCH, SwitchEntity
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
)

from .const import (
    KEY_COORDINATOR,
    KEY_ENTITIES,
    DOMAIN,
    CONF_TYPE,
    )
from . import MideaEntity, get_midea_config

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Midea Smart device from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]
    _LOGGER.debug("coordinator: {}".format(hass.data[DOMAIN][config_entry.entry_id]))
    config_type = config_entry.data[CONF_TYPE]
    entities = []
    for entity_key, config in get_midea_config(config_type, KEY_ENTITIES).items():
        if config["type"] == "switch":
            _LOGGER.debug("add switch device", entity_key, config)
            entities.append(MideaSwitchEntity(coordinator, entity_key))

    async_add_entities(entities)


class MideaSwitchEntity(MideaEntity, SwitchEntity):
    
    def __init__(self, coordinator, entity_key):
        """Initialize the Midea device."""
        super().__init__(coordinator, entity_key)

    @property
    def icon(self):
        """Return the icon for the device."""
        return self._config.get("icon", "mdi:power-plug")

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_SWITCH

    @property
    def is_on(self):
        """Return if the light is turned on."""
        return self._device.prompt_tone
    
    @property
    def state(self):
        """Return the state of the device."""
        state = getattr(self._device, self._config["property"])
        return STATE_ON if state else STATE_OFF

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        # self._device.prompt_tone = True
        setattr(self._device, self._config["property"], True)
        await self._coordinator.apply_changes()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        setattr(self._device, self._config["property"], False)
        await self._coordinator.apply_changes()
        self.async_write_ha_state()

