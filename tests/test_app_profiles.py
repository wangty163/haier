import unittest
from unittest import IsolatedAsyncioTestCase

from homeassistant.const import Platform

from custom_components.haier.core.app_profile import get_cloud_preferences
from custom_components.haier.core.attribute import V1SpecAttributeParser
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
        self.assertEqual(buzzer.display_name, "蜂鸣音开关")
        self.assertNotIn("invert_bool", buzzer.ext)
        self.assertEqual(hardness.display_name, "水软档位")
        self.assertEqual(hardness.options["native_min_value"], 0)
        self.assertEqual(hardness.options["native_max_value"], 5)
        self.assertEqual(hardness.options["native_step"], 1)

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
        self.assertEqual(purification.options["options"], ["执行"])
        self.assertEqual(valley_start.platform, Platform.TIME)
        self.assertEqual(
            valley_start.display_name,
            "分时用电谷段开始时间",
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
