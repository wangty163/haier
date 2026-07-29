from homeassistant.const import Platform

DOMAIN = 'haier'

SUPPORTED_PLATFORMS = [
    Platform.BUTTON,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.WATER_HEATER,
    Platform.COVER
]

FILTER_TYPE_INCLUDE = 'include'
FILTER_TYPE_EXCLUDE = 'exclude'
