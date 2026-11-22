"""Constants for the Govee LAN integration."""

from datetime import timedelta

DOMAIN = "govee_lan"
CONF_MODEL = "model"
SUPPORTED_MODELS = {"H6052", "H61C2", "H6056", "H6046"}
DEFAULT_NAME = "Govee LAN Light"
POLL_INTERVAL = timedelta(seconds=10)
CONTROL_PORT = 4003
RESPONSE_PORT = 4002
UDP_TIMEOUT = 3.0
