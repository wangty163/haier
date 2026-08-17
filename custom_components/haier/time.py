import logging
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import async_register_entity
from .core.attribute import HaierAttribute
from .core.device import HaierDevice
from .entity import HaierAbstractEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.TIME,
        lambda device, attribute: HaierTime(device, attribute),
    )


class HaierTime(HaierAbstractEntity, TimeEntity):

    def __init__(self, device: HaierDevice, attribute: HaierAttribute):
        super().__init__(device, attribute)

    def _update_value(self):
        value = self._attributes_data.get(self._attribute.key)
        if value in (None, ''):
            self._attr_native_value = None
            return

        try:
            self._attr_native_value = time.fromisoformat(str(value))
        except ValueError:
            _LOGGER.warning(
                'Device [%s] attribute [%s] time value [%s] not recognizable',
                self._device.id,
                self._attribute.key,
                value,
            )
            self._attr_native_value = None

    def set_value(self, value: time) -> None:
        self._send_command({
            self._attribute.key: value.strftime('%H:%M')
        })
