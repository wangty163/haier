from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import async_register_entity
from .core.attribute import HaierAttribute
from .core.device import HaierDevice
from .entity import HaierAbstractEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.BUTTON,
        lambda device, attribute: HaierButton(device, attribute),
    )


class HaierButton(HaierAbstractEntity, ButtonEntity):

    def __init__(self, device: HaierDevice, attribute: HaierAttribute):
        super().__init__(device, attribute)

    def _update_value(self):
        return

    def press(self) -> None:
        self._send_command({
            self._attribute.ext.get('data_key', self._attribute.key):
                self._attribute.ext['command_value']
        })
