"""Constants for the Midea Smart component."""
from datetime import timedelta

DOMAIN = "midea_smart"

# Config flow
CONF_HOST = "host"
CONF_TOKEN = "token"
CONF_DEVICE = "device"
CONF_MODEL = "model"
CONF_MAC = "mac"
CONF_ID = "id"
CONF_SSID = "ssid"
CONF_TYPE = "type"
CONF_VERSION = "version"
CONF_SN = "sn"
CONF_IP = "ip"
CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_PASSWORD = "cloud_password"
CONF_CLOUD_COUNTRY = "cloud_country"
CONF_MANUAL = "manual"
CONF_SCANNER = "scanner"
CONF_KEY = "key"

# Options flow
CONF_CLOUD_SUBDEVICES = "cloud_subdevices"

# Keys
KEY_COORDINATOR = "coordinator"
KEY_CONSTRUCTOR = "constructor"
KEY_DEVICE = "device"
KEY_TYPE = "type"
KEY_PLATFORMS = "platforms"
KEY_ENTITIES = "entities"

# Attributes
ATTR_AVAILABLE = "available"

COORDINATORS = "coordinators"

OPEN_MIDEA_APP_ACCOUNT = 'midea_is_best@outlook.com'
OPEN_MIDEA_APP_PASSWORD = 'lovemidea4ever'

MAX_ERRORS = 2
SCAN_INTERVAL = timedelta(seconds=15)

DEVICE_TYPES = {
    0xAC: "AC - air_conditioning",
    0xDB: "DB - front_load_washer",
}