"""Constants for the product-specific Enbrighten VIBE cloud integration."""

DOMAIN = "enbrighten_vibe"
VERSION = "0.1.1"
PRODUCT_ID = "wagmuetuwhn4lgr7"
CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_ENDPOINT = "endpoint"
CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 300
ENDPOINTS = {
    "https://openapi.tuyaus.com": "Western America",
    "https://openapi-ueaz.tuyaus.com": "Eastern America",
    "https://openapi.tuyaeu.com": "Central Europe",
    "https://openapi-weaz.tuyaeu.com": "Western Europe",
    "https://openapi.tuyacn.com": "China",
    "https://openapi.tuyain.com": "India",
}
DEFAULT_ENDPOINT = "https://openapi.tuyaus.com"
