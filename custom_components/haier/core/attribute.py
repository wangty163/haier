import logging
from abc import abstractmethod, ABC
from copy import deepcopy
from typing import List

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import Platform, UnitOfTemperature, PERCENTAGE, UnitOfVolume, UnitOfEnergy

from custom_components.haier.helpers import equals_ignore_case, contains_any_ignore_case
from .app_profile import get_app_profile

_LOGGER = logging.getLogger(__name__)

class HaierAttribute:

    def __init__(
        self,
        key: str,
        display_name: str,
        platform: Platform,
        options: dict | None = None,
        ext: dict | None = None,
    ):
        self._key = key
        self._display_name = display_name
        self._platform = platform
        self._options = options or {}
        self._ext = ext or {}

    @property
    def key(self) -> str:
        return self._key

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def platform(self) -> Platform:
        return self._platform

    @property
    def options(self) -> dict:
        return self._options

    @property
    def ext(self) -> dict:
        return self._ext


class HaierAttributeParser(ABC):

    @abstractmethod
    def parse_attribute(self, attribute: dict) -> HaierAttribute:
        pass

    @abstractmethod
    def parse_global(self, attributes: List[dict]):
        pass

class V1SpecAttributeParser(HaierAttributeParser, ABC):

    def __init__(self, product_code: str | None = None, product_name: str | None = None):
        self._app_profile = get_app_profile(product_code, product_name)

    def parse_attribute(self, attribute: dict) -> HaierAttribute:
        profile = self._app_profile.get(attribute.get('name'), {})

        # 通用模型里大量无值字段是工程命令。只有官方 App profile 明确列出的
        # 命令或设置才允许创建实体。
        if 'value' not in attribute and not profile.get('include_without_value'):
            return None

        attribute = self._apply_profile(attribute, profile)
        platform = profile.get('platform')

        if platform == Platform.BUTTON:
            return HaierAttribute(
                attribute['name'],
                attribute['desc'],
                Platform.BUTTON,
                ext={
                    'data_key': attribute['name'],
                    'command_value': profile['command_value'],
                },
            )

        if platform == Platform.TIME:
            return HaierAttribute(
                attribute['name'],
                attribute['desc'],
                Platform.TIME,
            )

        if not attribute.get('writable') and attribute.get('readable'):
            result = self._parse_as_sensor(attribute)
            return self._decorate(result, profile)

        if attribute.get('writable') and equals_ignore_case(attribute['valueRange']['type'], 'STEP') and contains_any_ignore_case(attribute['valueRange']['dataStep']['dataType'], ['Integer', 'Double']):
            result = self._parse_as_number(attribute)
            return self._decorate(result, profile)

        # 一定要在select之前，不然会被select覆盖
        if attribute.get('writable') and V1SpecAttributeParser._is_binary_attribute(attribute):
            result = self._parse_as_switch(attribute)
            return self._decorate(result, profile)

        if attribute.get('writable') and equals_ignore_case(attribute['valueRange']['type'], 'LIST'):
            result = self._parse_as_select(attribute)
            return self._decorate(result, profile)

        return None

    def parse_global(self, attributes: List[dict]):
        all_attribute_keys = [attribute['name'] for attribute in attributes]

        # 空调特征字段
        climate_feature_fields = [
            ['targetTemperature', 'operationMode', 'windSpeed'],
            # https://github.com/banto6/haier/issues/53 有空调分左右风区
            ['targetTemperature', 'operationMode', 'windSpeedL', 'windSpeedR']
        ]
        for feature_fields in climate_feature_fields:
            if len(list(set(feature_fields) - set(all_attribute_keys))) == 0:
                yield self._parse_as_climate(attributes, feature_fields)
                break

        # 燃气热水器
        if 'outWaterTemp' in all_attribute_keys and 'targetTemp' in all_attribute_keys and 'totalUseGasL' in all_attribute_keys:
            yield self._parse_as_gas_water_heater(attributes)

        # 窗帘
        if 'openDegree' in all_attribute_keys:
            yield self._parse_as_cover(attributes)

        # 洗碗机/洗衣机：对只读LIST类型的洗涤模式属性，保留原Sensor作为状态读取，
        # 同时额外生成Select实体用于在HA中切换模式
        _control_attrs = {'washprog', 'partitionwashstatus', 'runningmode'}
        for attr in attributes:
            profile = self._app_profile.get(attr.get('name'), {})
            needs_companion_select = (
                attr.get('name', '').lower() in _control_attrs
                or profile.get('companion_select')
            )
            if needs_companion_select \
                    and equals_ignore_case(attr['valueRange']['type'], 'LIST'):
                profiled_attr = self._apply_profile(attr, profile)
                allowed_values = profile.get('companion_allowed_values')
                data_list = profiled_attr['valueRange']['dataList']
                if allowed_values:
                    data_list = [
                        item
                        for item in data_list
                        if str(item['data']) in allowed_values
                    ]
                value_comparison_table = {}
                for item in data_list:
                    value_comparison_table[str(item['data'])] = item['desc']
                    value_comparison_table[str(item['desc'])] = item['data']
                yield HaierAttribute(
                    profiled_attr['name'] + '_sel',
                    profiled_attr['desc'],
                    Platform.SELECT,
                    {'options': [item['desc'] for item in data_list]},
                    {'value_comparison_table': value_comparison_table, 'data_key': profiled_attr['name']}
                )

    @staticmethod
    def _apply_profile(attribute: dict, profile: dict) -> dict:
        if not profile:
            return attribute

        result = deepcopy(attribute)
        result['desc'] = profile.get('display_name', result.get('desc'))

        if 'number_range' in profile:
            min_value, max_value, step = profile['number_range']
            data_step = result['valueRange']['dataStep']
            data_step['minValue'] = str(min_value)
            data_step['maxValue'] = str(max_value)
            data_step['step'] = str(step)

        value_descriptions = profile.get('value_descriptions', {})
        for item in result.get('valueRange', {}).get('dataList', []):
            replacement = value_descriptions.get(str(item.get('data')).lower())
            if replacement:
                item['desc'] = replacement

        return result

    @staticmethod
    def _decorate(attribute: HaierAttribute, profile: dict) -> HaierAttribute:
        if not profile:
            return attribute

        ext = dict(attribute.ext)
        if profile.get('invert_bool'):
            ext['invert_bool'] = True

        return HaierAttribute(
            attribute.key,
            profile.get('display_name', attribute.display_name),
            attribute.platform,
            dict(attribute.options),
            ext,
        )

    @staticmethod
    def _parse_as_sensor(attribute):
        if V1SpecAttributeParser._is_binary_attribute(attribute):
            return HaierAttribute(attribute['name'], attribute['desc'], Platform.BINARY_SENSOR)

        options = {}
        ext = {}
        if equals_ignore_case(attribute['valueRange']['type'], 'LIST'):
            value_comparison_table = {}
            for item in attribute['valueRange']['dataList']:
                value_comparison_table[str(item['data'])] = item['desc']

            options['device_class'] = SensorDeviceClass.ENUM
            options['options'] = list(value_comparison_table.values())
            ext['value_comparison_table'] = value_comparison_table

        if equals_ignore_case(attribute['valueRange']['type'], 'STEP'):
            state_class, device_class, unit = V1SpecAttributeParser._guess_state_class_device_class_and_unit(attribute)
            if device_class:
                options['device_class'] = device_class

            if state_class:
                options['state_class'] = state_class

            if unit:
                options['native_unit_of_measurement'] = unit

        return HaierAttribute(attribute['name'], attribute['desc'], Platform.SENSOR, options, ext)

    @staticmethod
    def _parse_as_number(attribute):
        step = attribute['valueRange']['dataStep']
        options = {
            'native_min_value': float(step['minValue']),
            'native_max_value': float(step['maxValue']),
            'native_step': float(step['step'])
        }

        _, _, unit = V1SpecAttributeParser._guess_state_class_device_class_and_unit(attribute)
        if unit:
            options['native_unit_of_measurement'] = unit

        return HaierAttribute(attribute['name'], attribute['desc'], Platform.NUMBER, options)

    @staticmethod
    def _parse_as_select(attribute):
        value_comparison_table = {}
        for item in attribute['valueRange']['dataList']:
            value_comparison_table[str(item['data'])] = item['desc']
            value_comparison_table[str(item['desc'])] = item['data']

        ext = {
            'value_comparison_table': value_comparison_table,
            'stateless': len(attribute['valueRange']['dataList']) == 1,
        }

        options = {
            'options': [item['desc'] for item in attribute['valueRange']['dataList']]
        }

        return HaierAttribute(attribute['name'], attribute['desc'], Platform.SELECT, options, ext)

    @staticmethod
    def _parse_as_switch(attribute):
        options = {
            'device_class': SwitchDeviceClass.SWITCH
        }

        return HaierAttribute(attribute['name'], attribute['desc'], Platform.SWITCH, options)

    @staticmethod
    def _parse_as_climate(attributes: List[dict], feature_fields: List[str]):
        for attr in attributes:
            if attr['name'] == 'targetTemperature':
                target_temperature_attr = attr
                break
        else:
            raise RuntimeError('targetTemperature attr not found')

        options = {
            'min_temp': float(target_temperature_attr['valueRange']['dataStep']['minValue']),
            'max_temp': float(target_temperature_attr['valueRange']['dataStep']['maxValue']),
            'target_temperature_step': float(target_temperature_attr['valueRange']['dataStep']['step'])
        }

        ext = {
            'customize': True,
            # 是否存在多个风口
            'exist_multiple_vents': 'windSpeedL' in feature_fields
        }

        return HaierAttribute('climate', 'Climate', Platform.CLIMATE, options, ext)

    @staticmethod
    def _parse_as_gas_water_heater(attributes: List[dict]):
        for attr in attributes:
            if attr['name'] == 'targetTemp':
                target_temperature_attr = attr
                break
        else:
            raise RuntimeError('targetTemp attr not found')

        options = {
            'min_temp': target_temperature_attr['valueRange']['dataStep']['minValue'],
            'max_temp': target_temperature_attr['valueRange']['dataStep']['maxValue'],
            'target_temperature_step': target_temperature_attr['valueRange']['dataStep']['step']
        }

        ext = {
            'customize': True,
        }

        return HaierAttribute('gas_water_heater', 'GasWaterHeater', Platform.WATER_HEATER, options, ext)

    @staticmethod
    def _parse_as_cover(attributes: List[dict]):
        for attr in attributes:
            if attr["name"] == "openDegree":
                step = attr['valueRange']['dataStep']
        options = {
            'native_min_value': float(step['minValue']),
            'native_max_value': float(step['maxValue']),
            'native_step': step['step']
        }
        ext = {
            'customize': True,
        }
        return HaierAttribute('cover', 'Cover', Platform.COVER, options,ext)

    @staticmethod
    def _is_binary_attribute(attribute):
        valueRange = attribute['valueRange']

        return (equals_ignore_case(valueRange['type'], 'LIST')
                and len(valueRange['dataList']) == 2
                and contains_any_ignore_case(valueRange['dataList'][0]['data'], ['true', 'false'])
                and contains_any_ignore_case(valueRange['dataList'][1]['data'], ['true', 'false']))

    @staticmethod
    def _guess_state_class_device_class_and_unit(attribute) -> (str, str, str):
        """
        猜测 state class, device class和unit
        :return:
        """

        state_class = None

        if '累计' in attribute['desc']:
            state_class = SensorStateClass.TOTAL
        
        if '本次' in attribute['desc']:
            state_class = SensorStateClass.TOTAL_INCREASING

        if '温度' in attribute['desc']:
            return state_class, SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS

        if '湿度' in attribute['desc']:
            return state_class, SensorDeviceClass.HUMIDITY, PERCENTAGE

        if '用水量' in attribute['desc']:
            return state_class, SensorDeviceClass.WATER, UnitOfVolume.LITERS

        if '用气量' in attribute['desc']:
            return state_class, SensorDeviceClass.GAS, UnitOfVolume.LITERS

        if '用电量' in attribute['desc']:
            return state_class, SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR

        return state_class, None, None
