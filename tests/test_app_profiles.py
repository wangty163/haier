import unittest
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import Platform

from custom_components.haier import _remove_stale_profile_entities
from custom_components.haier.binary_sensor import HaierBinarySensor
from custom_components.haier.core.app_profile import get_cloud_preferences
from custom_components.haier.core.attribute import (
    HaierAttribute,
    V1SpecAttributeParser,
)
from custom_components.haier.core.device import HaierDevice


def list_attribute(
    name,
    desc,
    data_list,
    *,
    value=None,
    include_value=True,
    writable=True,
    readable=True,
):
    attribute = {
        "name": name,
        "desc": desc,
        "writable": writable,
        "readable": readable,
        "valueRange": {
            "type": "LIST",
            "dataList": [
                {"data": data, "desc": item_desc}
                for data, item_desc in data_list
            ],
        },
    }
    if include_value:
        attribute["value"] = value
    return attribute


def step_attribute(
    name,
    desc,
    *,
    value=None,
    include_value=True,
    writable=True,
    readable=True,
    minimum=0,
    maximum=24,
    step=1,
):
    attribute = {
        "name": name,
        "desc": desc,
        "writable": writable,
        "readable": readable,
        "valueRange": {
            "type": "STEP",
            "dataStep": {
                "dataType": "Integer",
                "minValue": str(minimum),
                "maxValue": str(maximum),
                "step": str(step),
            },
        },
    }
    if include_value:
        attribute["value"] = value
    return attribute


class DishwasherAppProfileTest(unittest.TestCase):
    def setUp(self):
        self.parser = V1SpecAttributeParser("FA08JM001", "CWC10-B29BKU1")

    def test_official_names_and_ranges(self):
        strong = self.parser.parse_attribute(
            list_attribute(
                "strongStatus",
                "加强洗功能状态",
                [(False, "关"), (True, "开")],
                value=False,
            )
        )
        buzzer = self.parser.parse_attribute(
            list_attribute(
                "buzzerDisabled",
                "蜂鸣音静音",
                [(False, "蜂鸣器不静音"), (True, "蜂鸣器静音")],
                value=False,
            )
        )
        hardness = self.parser.parse_attribute(
            step_attribute(
                "hardnessLevel",
                "设定的水硬度档位",
                value=1,
                maximum=9,
            )
        )

        self.assertEqual(strong.display_name, "加强")
        self.assertEqual(buzzer.display_name, "蜂鸣音")
        self.assertTrue(buzzer.ext["invert_bool"])
        self.assertEqual(hardness.display_name, "水软档位")
        self.assertEqual(hardness.options["native_min_value"], 0)
        self.assertEqual(hardness.options["native_max_value"], 5)
        self.assertEqual(hardness.options["native_step"], 1)

    def test_status_is_not_exposed_as_a_switch(self):
        malformed_door = self.parser.parse_attribute(
            list_attribute(
                "doorStatus",
                "门状态",
                [(True, "开"), (False, "关")],
                value=False,
            )
        )
        door = self.parser.parse_attribute(
            list_attribute(
                "doorCloseStatus",
                "关门状态",
                [(False, "未关门"), (True, "已关门")],
                value=True,
                writable=False,
            )
        )
        legacy_control = self.parser.parse_attribute(
            list_attribute(
                "projectionLampStatus",
                "投影灯状态",
                [(False, "关"), (True, "开")],
                value=False,
            )
        )

        self.assertIsNone(malformed_door)
        self.assertIsNone(legacy_control)
        self.assertEqual(door.platform, Platform.BINARY_SENSOR)
        self.assertEqual(door.display_name, "门状态")
        self.assertEqual(
            door.options["device_class"],
            BinarySensorDeviceClass.DOOR,
        )
        self.assertTrue(door.ext["invert_bool"])

    def test_app_controls_keep_semantic_platforms(self):
        strong = self.parser.parse_attribute(
            list_attribute(
                "strongStatus",
                "加强洗功能状态",
                [(False, "关"), (True, "开")],
                value=False,
            )
        )
        power_on = self.parser.parse_attribute(
            list_attribute(
                "onOffStatus",
                "开关机状态",
                [(True, "开机")],
                value=False,
            )
        )

        self.assertEqual(strong.platform, Platform.SWITCH)
        self.assertEqual(power_on.platform, Platform.BUTTON)
        self.assertEqual(power_on.ext["command_value"], "true")

    def test_reservation_uses_official_app_range_without_snapshot_value(self):
        reservation = self.parser.parse_attribute(
            step_attribute(
                "resnTime",
                "预约时间",
                include_value=False,
                readable=False,
            )
        )

        self.assertEqual(reservation.platform, Platform.NUMBER)
        self.assertEqual(reservation.display_name, "预约")
        self.assertEqual(reservation.options["native_min_value"], 1)
        self.assertEqual(reservation.options["native_max_value"], 12)

    def test_stop_program_is_added_but_unverified_engineering_commands_are_not(self):
        stop = self.parser.parse_attribute(
            list_attribute(
                "returnStandby",
                "终止当前运行状态回到待机状态",
                [("1", "执行")],
                include_value=False,
                writable=False,
                readable=False,
            )
        )
        factory_reset = self.parser.parse_attribute(
            list_attribute(
                "specialFunction",
                "特殊设置",
                [("1", "恢复出厂设置")],
                include_value=False,
                readable=False,
            )
        )

        self.assertEqual(stop.platform, Platform.BUTTON)
        self.assertEqual(stop.display_name, "终止程序")
        self.assertEqual(stop.ext["command_value"], "1")
        self.assertIsNone(factory_reset)

    def test_wash_program_control_excludes_non_app_empty_program(self):
        wash_program = list_attribute(
            "washProg",
            "洗涤程序",
            [
                ("0", "空流程"),
                ("3", "强力"),
                ("10", "酒具"),
                ("22", "智能"),
                ("27", "水果"),
                ("41", "日常"),
                ("42", "超快"),
            ],
            value="41",
            writable=False,
        )

        controls = list(self.parser.parse_global([wash_program]))

        self.assertEqual(
            controls[0].options["options"],
            ["强力", "酒具", "智能", "水果", "日常", "超快"],
        )

    def test_running_state_and_control_have_distinct_semantics(self):
        running_mode = list_attribute(
            "runningMode",
            "运行状态",
            [("1", "启动"), ("2", "暂停")],
            value="2",
            writable=False,
        )

        state = self.parser.parse_attribute(running_mode)
        controls = list(self.parser.parse_global([running_mode]))

        self.assertEqual(state.platform, Platform.SENSOR)
        self.assertEqual(state.display_name, "运行状态")
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0].platform, Platform.SELECT)
        self.assertEqual(controls[0].display_name, "运行控制")

    def test_writable_non_app_select_has_no_duplicate_control(self):
        partition_wash = list_attribute(
            "partitionWashStatus",
            "分区洗功能状态",
            [
                ("0", "取消分区洗"),
                ("1", "下层洗"),
                ("2", "上层洗"),
            ],
            value="0",
        )

        self.assertIsNone(self.parser.parse_attribute(partition_wash))
        self.assertEqual(
            list(self.parser.parse_global([partition_wash])),
            [],
        )

    def test_cloud_preference_names_match_official_app(self):
        self.assertEqual(
            get_cloud_preferences("FA08JM001", "CWC10-B29BKU1"),
            {
                "startReminderStatus": "启动提醒",
                "wash_report": "洗完提醒",
                "salt_lack": "专用盐不足提醒",
                "brightener_lack": "漂洗剂不足提醒",
                "cleaningReminderStatus": "滤网清洁提醒",
                "sprayArmStopNoticeStatus": "喷淋臂停转提醒",
                "aiStatus": "AI识水",
                "hotWind": "热风烘干",
                "peakValleyElectricSwitch": "峰谷电开关",
            },
        )


class FridgeAppProfileTest(unittest.TestCase):
    def setUp(self):
        self.parser = V1SpecAttributeParser("B00Y10000", "BCD-450WGCFDM4WNU1")

    def test_temperatures_keep_state_sensor_and_gain_app_control_select(self):
        freezer = list_attribute(
            "freezerTargetTempLevel",
            "冷冻室",
            [("12", "-18"), ("13", "-17")],
            value="12",
            writable=False,
        )

        state = self.parser.parse_attribute(freezer)
        controls = list(self.parser.parse_global([freezer]))

        self.assertEqual(state.platform, Platform.SENSOR)
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0].key, "freezerTargetTempLevel_sel")
        self.assertEqual(controls[0].display_name, "冷冻室")
        self.assertEqual(controls[0].options["options"], ["-18", "-17"])
        self.assertEqual(
            controls[0].ext["value_comparison_table"]["-18"],
            "12",
        )

    def test_purification_and_time_settings_use_official_app_text(self):
        purification = self.parser.parse_attribute(
            list_attribute(
                "refSterilizationForcedOn",
                "强制开启冷藏室杀菌",
                [(True, "开")],
                value=False,
            )
        )
        valley_start = self.parser.parse_attribute({
            "name": "sharingElectricityStartTime",
            "desc": "分时用电谷段开始时间",
            "writable": True,
            "readable": True,
            "valueRange": {"type": "TIME"},
        })

        self.assertEqual(purification.display_name, "冷藏室开启净化")
        self.assertEqual(purification.platform, Platform.BUTTON)
        self.assertEqual(purification.ext["command_value"], "true")
        self.assertEqual(valley_start.platform, Platform.TIME)
        self.assertEqual(
            valley_start.display_name,
            "分时用电谷段开始时间",
        )

    def test_door_statuses_are_door_binary_sensors(self):
        door = self.parser.parse_attribute(
            list_attribute(
                "refrigeratorDoorStatus",
                "冷藏室门开关状态",
                [(True, "开"), (False, "关")],
                value=False,
                writable=False,
            )
        )

        self.assertEqual(door.platform, Platform.BINARY_SENSOR)
        self.assertEqual(door.display_name, "冷藏室门状态")
        self.assertEqual(
            door.options["device_class"],
            BinarySensorDeviceClass.DOOR,
        )


class GenericProductSemanticsTest(unittest.TestCase):
    def test_unknown_products_keep_generic_writable_attributes(self):
        parser = V1SpecAttributeParser("UNKNOWN", "UNKNOWN")
        attribute = parser.parse_attribute(
            list_attribute(
                "doorStatus",
                "门状态",
                [(True, "开"), (False, "关")],
                value=False,
            )
        )

        self.assertEqual(attribute.platform, Platform.SWITCH)


class EntitySemanticsMigrationTest(unittest.TestCase):
    def test_closed_door_value_is_off_for_ha_door_sensor(self):
        device = SimpleNamespace(
            id="dishwasher-id",
            name="洗碗机",
            product_name="CWC10-B29BKU1",
        )
        attribute = HaierAttribute(
            "doorCloseStatus",
            "门状态",
            Platform.BINARY_SENSOR,
            {"device_class": BinarySensorDeviceClass.DOOR},
            {"invert_bool": True},
        )
        entity = HaierBinarySensor(device, attribute)
        entity._attributes_data = {"doorCloseStatus": "true"}

        entity._update_value()

        self.assertIs(entity.is_on, False)

    def test_stale_and_changed_platform_entities_are_removed(self):
        registry = SimpleNamespace(
            async_remove=lambda entity_id: removed.append(entity_id),
        )
        removed = []
        entries = [
            SimpleNamespace(
                platform="haier",
                unique_id="haier.abc_doorstatus",
                entity_id="switch.old_door_status",
            ),
            SimpleNamespace(
                platform="haier",
                unique_id="haier.abc_onoffstatus",
                entity_id="select.old_power_on",
            ),
            SimpleNamespace(
                platform="haier",
                unique_id="haier.abc_doorclosestatus",
                entity_id="binary_sensor.door_status",
            ),
            SimpleNamespace(
                platform="haier",
                unique_id="haier.other_doorstatus",
                entity_id="switch.other_device",
            ),
        ]
        device = SimpleNamespace(
            id="ABC",
            product_code="FA08JM001",
            product_name="CWC10-B29BKU1",
            attributes=[
                HaierAttribute(
                    "doorCloseStatus",
                    "门状态",
                    Platform.BINARY_SENSOR,
                ),
                HaierAttribute(
                    "onOffStatus",
                    "开机",
                    Platform.BUTTON,
                ),
            ],
        )

        with (
            patch(
                "custom_components.haier.er.async_get",
                return_value=registry,
            ),
            patch(
                "custom_components.haier.er.async_entries_for_config_entry",
                return_value=entries,
            ),
        ):
            _remove_stale_profile_entities(
                SimpleNamespace(),
                SimpleNamespace(entry_id="entry-id"),
                [device],
            )

        self.assertEqual(
            removed,
            [
                "switch.old_door_status",
                "select.old_power_on",
            ],
        )


class FakeDishwasherClient:
    def __init__(self):
        self.set_calls = []

    async def get_digital_model_from_cache(self, device):
        return []

    async def get_dishwasher_preferences(self, device_id):
        return {
            "aiStatus": {
                "display_name": "AI识水",
                "value": True,
                "unit_index": 0,
            },
            "cleaningReminderStatus": {
                "display_name": "滤网清洁提醒",
                "value": False,
                "unit_index": 0,
            },
        }

    async def set_dishwasher_preference(self, device_id, preference, value):
        self.set_calls.append((device_id, preference, value))


class DishwasherCloudEntityTest(IsolatedAsyncioTestCase):
    async def test_cloud_preferences_are_added_and_writable(self):
        client = FakeDishwasherClient()
        device = HaierDevice(
            client,
            {
                "deviceId": "dishwasher-id",
                "deviceName": "洗碗机",
                "deviceType": "0A00201K",
                "productCodeT": "FA08JM001",
                "productNameT": "CWC10-B29BKU1",
                "wifiType": "wifi",
            },
        )

        await device.async_init()

        attributes = {item.key: item for item in device.attributes}
        self.assertEqual(
            attributes["cloud_aiStatus"].display_name,
            "AI识水",
        )
        self.assertTrue(
            attributes["cloud_aiStatus"].ext["initial_value"],
        )
        self.assertFalse(
            attributes["cloud_cleaningReminderStatus"].ext["initial_value"],
        )

        await device.async_set_cloud_preference(
            "cleaningReminderStatus",
            True,
        )
        self.assertEqual(
            client.set_calls,
            [("dishwasher-id", "cleaningReminderStatus", True)],
        )


if __name__ == "__main__":
    unittest.main()
