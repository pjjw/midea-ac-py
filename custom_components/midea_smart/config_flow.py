"""Config flow to configure Midea Smart devices."""
from . import get_midea_config
from msmart.cloud import cloud as midea_cloud
from msmart.const import (
    OPEN_MIDEA_APP_ACCOUNT,
    OPEN_MIDEA_APP_PASSWORD,
)
from .const import (
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    CONF_KEY,
    CONF_VERSION,
    CONF_TYPE,
    CONF_SSID,
    CONF_MODEL,
    CONF_SN,
    CONF_IP,
    DOMAIN,
    DEVICE_TYPES,
    KEY_CONSTRUCTOR,
)
from msmart.scanner import MideaDiscovery, get_udpid
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_ID, CONF_PORT, CONF_TOKEN
from homeassistant import config_entries
import voluptuous as vol
import logging
_LOGGER = logging.getLogger(__name__)


class MideaSmartFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Midea Smart config flow."""

    def __init__(self):
        """Initialize the flow."""
        self.devices = {}

        self.version = 2
        self.name = ""
        self.host = "192.168."
        self.port = 6444
        self.id = None
        self.type = 0xff
        self.token = ""
        self.key = ""

        self.sn = vol.UNDEFINED
        self.model = vol.UNDEFINED
        self.ssid = vol.UNDEFINED

        # self.cloud_devices = {}
        self._device_list = {}
        self._verify = False
        self._step = None
        self._actions = {
            'scanner': 'Scan for new devices',
            'manual': 'Add a device manually',
        }

    def extract_device_info(self, info):
        """Extract the device info."""
        _LOGGER.info("extract_device_info: {}".format(info))
        self.name = info.get(CONF_NAME, self.name)
        self.host = info.get(CONF_IP, self.host)
        self.port = info.get(CONF_PORT, self.port)
        self.id = info.get(CONF_ID, self.id)
        self.type = info.get(CONF_TYPE, self.type)
        if type(self.type) == str:
            self.type = int(self.type, 16)
        self.version = info.get(CONF_VERSION, self.version)
        self.token = info.get(CONF_TOKEN, self.token)
        if self.token is None:
            self.token = ""
        self.key = info.get(CONF_KEY, self.key)
        if self.key is None:
            self.key = ""

        self.sn = info.get(CONF_SN, self.sn)
        self.model = info.get(CONF_MODEL, self.model)
        self.ssid = info.get(CONF_SSID, self.ssid)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            if user_input['action'] == "manual":
                return await self.async_step_device_info()
            else:
                return await self.async_step_scanner(user_input)

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required('action', default="scanner"): vol.In({'scanner': 'Scan to add a device', 'manual': 'Add a device manually'})
            }),
            errors=errors
        )

    async def async_step_scanner(self, user_input=None):
        """Handle scan for new devices."""
        midea_discovery = MideaDiscovery(
            account=OPEN_MIDEA_APP_ACCOUNT, password=OPEN_MIDEA_APP_PASSWORD)
        midea_discovery.run_test = False
        found_devices = await midea_discovery.get_all()
        for device in found_devices:
            s = ""
            if int(device.type, 16) not in DEVICE_TYPES:
                s = "unsupported"
            self.devices[device.name] = device
            self._device_list[device.name] = "{} (ver: {} {}) {} ".format(
                device.name, device.version, s, device.ip)

        if len(self.devices) > 0:
            return await self.async_step_select()

        return self.async_abort(reason="no_found_devices")

    async def async_step_select(self, user_input=None):
        """Handle multiple devices found."""
        errors = {}
        if user_input is not None:
            device_name = user_input['select']
            device = self.devices[device_name]
            self._device = device
            self.extract_device_info(device.__dict__)
            if self.type not in DEVICE_TYPES:
                return self.async_abort(reason="unspported_device")
            if device.version == 2:
                return await self.async_step_device_info({'version': 2, 'step': 'select'})
            elif device.version == 3:
                return await self.async_step_cloud()

        select_schema = vol.Schema(
            {vol.Required("select", default=list(self._device_list)[
                          0]): vol.In(self._device_list)}
        )

        return self.async_show_form(
            step_id="select", data_schema=select_schema, errors=errors
        )

    async def async_step_device_info(self, user_input=None):
        """Handle device info input."""
        errors = {}
        if user_input is not None:
            self.name = user_input.get(CONF_NAME, self.name)
            self.host = user_input.get(CONF_HOST, self.host)
            self.port = user_input.get(CONF_PORT, self.port)
            self.id = user_input.get(CONF_ID, self.id)
            self.token = user_input.get(CONF_TOKEN, self.token)
            self.key = user_input.get(CONF_KEY, self.key)

            self.version = user_input.get(CONF_VERSION, self.version)
            self._step = user_input.get('step', "device_info")

            if self.version == 2:
                select_schema = vol.Schema({
                    vol.Required(CONF_NAME, default=self.name): str,
                    vol.Required(CONF_TYPE, default=self.type): vol.In(DEVICE_TYPES),
                    vol.Required(CONF_HOST, default=self.host): str,
                    vol.Required(CONF_PORT, default=self.port): int,
                    vol.Required(CONF_ID, default=self.id): int,
                })
                # manual input
                if self._step == "device_info" and self.name != "":
                    self.extract_device_info(user_input)
                    if self._verify:
                        return await self.async_step_setting()
                    else:
                        verify = await self.async_step_verify()
                        if verify:
                            return await self.async_step_setting()
                        else:
                            errors = {'base': 'verify_failed'}

                return self.async_show_form(
                    step_id="device_info", data_schema=select_schema, errors=errors
                )

            elif self.version == 3:
                select_schema = vol.Schema({
                    vol.Required(CONF_NAME, default=self.name): str,
                    vol.Required(CONF_TYPE, default=self.type): vol.In(DEVICE_TYPES),
                    vol.Required(CONF_HOST, default=self.host): str,
                    vol.Required(CONF_PORT, default=self.port): int,
                    vol.Required(CONF_ID, default=self.id): int,
                    vol.Required(CONF_TOKEN, default=self.token): str,
                    vol.Required(CONF_KEY, default=self.key): str,
                })
                # manual input
                if self._step == "device_info" and self.name != "":
                    self.extract_device_info(user_input)
                    if self._verify:
                        return await self.async_step_setting()
                    else:
                        verify = await self.async_step_verify()
                        if verify:
                            return await self.async_step_setting()
                        else:
                            errors = {'base': 'verify_failed'}

                return self.async_show_form(
                    step_id="device_info", data_schema=select_schema, errors=errors
                )

        select_schema = vol.Schema({
            vol.Required(CONF_VERSION, default=self.version): vol.In({2: 'ver2', 3: 'ver3'}),
        })

        return self.async_show_form(
            step_id="device_info", data_schema=select_schema, errors=errors
        )

    async def async_step_setting(self, user_input=None):
        """Handle device setting input."""
        errors = {}
        existing_entry = await self.async_set_unique_id(
            self.name, raise_on_progress=False
        )
        if existing_entry:
            return self.async_abort(reason="already_configured")

        conf_data = {}
        conf_data[CONF_NAME] = self.name
        conf_data[CONF_HOST] = self.host
        conf_data[CONF_PORT] = self.port
        conf_data[CONF_ID] = self.id
        conf_data[CONF_TOKEN] = self.token
        conf_data[CONF_KEY] = self.key
        conf_data[CONF_TYPE] = self.type
        conf_data[CONF_VERSION] = self.version

        _LOGGER.debug("config data: {}".format(conf_data))
        return self.async_create_entry(title=self.name, data=conf_data)

    async def async_step_verify(self, user_input=None):
        """Handle device verify input."""
        _LOGGER.debug("verify step")
        coordinator = get_midea_config(self.type, KEY_CONSTRUCTOR)
        if coordinator is None:
            return False
        _device = coordinator(self.host, self.id, self.port)
        _device.set_device_detail(self.__dict__)
        try:
            await self.hass.async_add_executor_job(_device.refresh)
            if _device.support:
                self._verify = True
                return True
        except Exception as e:
            _LOGGER.error("Authentication failed: {}".format(e))
        return False

    async def async_step_cloud(self, user_input=None):
        """Handle device cloud input."""
        errors = {}
        if user_input is not None:
            if user_input['use_open_account']:
                cloud_username = OPEN_MIDEA_APP_ACCOUNT
                cloud_password = OPEN_MIDEA_APP_PASSWORD
            else:
                cloud_username = user_input.get(CONF_CLOUD_USERNAME, "")
                cloud_password = user_input.get(CONF_CLOUD_PASSWORD, "")
            if cloud_username == "" or cloud_password == "":
                errors['base'] = "cloud_account_empty"
            else:
                _client = midea_cloud(cloud_username, cloud_password)
                for udpid in [get_udpid(self.id.to_bytes(6, 'little')), get_udpid(self.id.to_bytes(6, 'big'))]:
                    try:
                        token, key = await self.hass.async_add_executor_job(_client.gettoken, udpid)
                        if not token or not key:
                            errors['base'] = "token_key_empty"
                            break
                    except Exception as e:
                        _LOGGER.error("get token failed: {}".format(e))
                        errors['base'] = "cloud_auth_fail"
                        break
                    self.token, self.key = token, key
                    verify = await self.async_step_verify()
                    if verify:
                        self._verify = True
                        return await self.async_step_device_info({'version': 3, 'step': 'cloud'})
                    else:
                        continue

        DEVICE_CLOUD_CONFIG = vol.Schema({
            vol.Optional(CONF_CLOUD_USERNAME): str,
            vol.Optional(CONF_CLOUD_PASSWORD): str,
            vol.Optional("use_open_account", default=False): bool,
        })

        return self.async_show_form(
            step_id="cloud", data_schema=DEVICE_CLOUD_CONFIG, errors=errors
        )
