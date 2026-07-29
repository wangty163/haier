import json
import logging
from typing import List

from homeassistant.const import Platform

from .app_profile import get_cloud_preferences
from .attribute import HaierAttribute, V1SpecAttributeParser

_LOGGER = logging.getLogger(__name__)


class HaierDevice:
    _raw_data: dict
    _attributes: List[HaierAttribute]

    def __init__(self, client, raw: dict):
        self._client = client
        self._raw_data = raw
        self._attributes = []

    @property
    def id(self):
        return self._raw_data['deviceId']

    @property
    def name(self):
        return self._raw_data['deviceName'] if 'deviceName' in self._raw_data else self.id

    @property
    def type(self):
        return self._raw_data['deviceType'] if 'deviceType' in self._raw_data else None

    @property
    def product_code(self):
        return self._raw_data['productCodeT'] if 'productCodeT' in self._raw_data else None

    @property
    def product_name(self):
        return self._raw_data['productNameT'] if 'productNameT' in self._raw_data else None

    @property
    def wifi_type(self):
        return self._raw_data['wifiType']

    @property
    def attributes(self) -> List[HaierAttribute]:
        return self._attributes

    async def async_init(self):
        # 解析Attribute
        # noinspection PyBroadException
        try:
            parser = V1SpecAttributeParser(self.product_code, self.product_name)
            attributes = await self._client.get_digital_model_from_cache(self)
            for item in attributes:
                try:
                    attr = parser.parse_attribute(item)
                    if attr:
                        self._attributes.append(attr)
                except Exception:
                    _LOGGER.exception("Haier device %s attribute %s parsing error occurred", self.id, item['name'])

            iter = parser.parse_global(attributes)
            if iter:
                for item in iter:
                    self._attributes.append(item)

            cloud_preference_profile = get_cloud_preferences(
                self.product_code,
                self.product_name,
            )
            if cloud_preference_profile:
                await self._async_add_cloud_preferences(cloud_preference_profile)
        except Exception:
            _LOGGER.exception('Haier device %s init failed', self.id)

    async def _async_add_cloud_preferences(self, profile: dict) -> None:
        live_preferences = {}
        try:
            live_preferences = await self._client.get_dishwasher_preferences(
                self.id
            )
        except Exception:
            _LOGGER.exception(
                'Haier device %s App cloud preferences loading failed',
                self.id,
            )

        preferences = {
            key: {
                'display_name': display_name,
                'value': None,
                'unit_index': 0,
            }
            for key, display_name in profile.items()
        }
        preferences.update(live_preferences)
        # 蜂鸣音由设备属性直接控制；这里只避免云端设置接口重复建实体。
        preferences.pop('buzzerDisabled', None)

        for key, preference in preferences.items():
            self._attributes.append(HaierAttribute(
                'cloud_' + key,
                preference.get('display_name') or profile.get(key) or key,
                Platform.SWITCH,
                ext={
                    'cloud_preference': key,
                    'initial_value': preference.get('value'),
                    'unit_index': preference.get('unit_index', 0),
                },
            ))

    async def async_set_cloud_preference(
        self,
        preference: str,
        value: bool,
    ) -> None:
        await self._client.set_dishwasher_preference(
            self.id,
            preference,
            value,
        )

    def __str__(self) -> str:
        return json.dumps({
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'wifi_type': self.wifi_type
        })
