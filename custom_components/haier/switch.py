import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import async_register_entity
from .core.attribute import HaierAttribute
from .core.device import HaierDevice
from .entity import HaierAbstractEntity
from .helpers import try_read_as_bool

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.SWITCH,
        lambda device, attribute: HaierSwitch(device, attribute)
    )


class HaierSwitch(HaierAbstractEntity, SwitchEntity):

    def __init__(self, device: HaierDevice, attribute: HaierAttribute):
        super().__init__(device, attribute)
        if attribute.ext.get('cloud_preference'):
            self._attr_is_on = attribute.ext.get('initial_value')
            self._attr_available = self._attr_is_on is not None

    def _update_value(self):
        if self._attribute.ext.get('cloud_preference'):
            self._attr_available = self._attr_is_on is not None
            return

        value = self._attributes_data.get(self._attribute.key)
        if value in (None, ''):
            self._attr_is_on = None
            return

        try:
            is_on = try_read_as_bool(value)
            self._attr_is_on = (
                not is_on if self._attribute.ext.get('invert_bool') else is_on
            )
        except ValueError:
            _LOGGER.exception(
                'entity [%s] read value failed',
                self._attr_unique_id,
            )
            self._attr_available = False

    def turn_on(self, **kwargs: Any) -> None:
        self._send_command({
            self._attribute.key: not self._attribute.ext.get('invert_bool')
        })

    def turn_off(self, **kwargs: Any) -> None:
        self._send_command({
            self._attribute.key: bool(self._attribute.ext.get('invert_bool'))
        })

    async def async_turn_on(self, **kwargs: Any) -> None:
        preference = self._attribute.ext.get('cloud_preference')
        if not preference:
            self.turn_on(**kwargs)
            return

        await self._device.async_set_cloud_preference(preference, True)
        self._attr_is_on = True
        self._attr_available = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        preference = self._attribute.ext.get('cloud_preference')
        if not preference:
            self.turn_off(**kwargs)
            return

        await self._device.async_set_cloud_preference(preference, False)
        self._attr_is_on = False
        self._attr_available = True
        self.async_write_ha_state()
