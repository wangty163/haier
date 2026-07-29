"""Official App presentation and control overrides for verified products.

The generic digital model contains engineering attributes and sometimes reports
controls as temporarily read-only.  These profiles only describe controls that
are present in the official App for the matching product.
"""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import Platform

DISHWASHER_PROFILE = {
    "doorCloseStatus": {
        "display_name": "门状态",
        "entity_options": {
            "device_class": BinarySensorDeviceClass.DOOR,
        },
        # The model reports true when closed; HA door sensors are on when open.
        "invert_bool": True,
    },
    "runningMode": {
        "display_name": "运行状态",
        "companion_select": True,
        "companion_display_name": "运行控制",
        "companion_allowed_values": ("1", "2"),
    },
    "strongStatus": {"display_name": "加强"},
    "resnStatus": {"display_name": "预约"},
    "washProg": {
        "display_name": "洗涤程序",
        "companion_select": True,
        "companion_allowed_values": ("3", "10", "22", "27", "41", "42"),
    },
    "returnStandby": {
        "display_name": "终止程序",
        "include_without_value": True,
        "platform": Platform.BUTTON,
        "command_value": "1",
    },
    "rinseAddStatus": {"display_name": "漂洗"},
    "hardnessLevel": {
        "display_name": "水软档位",
        "number_range": (0, 5, 1),
    },
    "buzzerDisabled": {
        "display_name": "蜂鸣音",
        "invert_bool": True,
    },
    "onOffStatus": {
        "display_name": "开机",
        "platform": Platform.BUTTON,
        "command_value": "true",
    },
    "remoteCtrValid": {"display_name": "远程授权"},
    "resnTime": {
        "display_name": "预约",
        "include_without_value": True,
        "number_range": (1, 12, 1),
    },
    "brightenerWeight": {
        "display_name": "光亮剂档位",
        "number_range": (0, 5, 1),
    },
    "disinfectStatus": {"display_name": "消毒"},
    "dryStatus": {"display_name": "干燥"},
}

DISHWASHER_CLOUD_PREFERENCES = {
    "startReminderStatus": "启动提醒",
    "wash_report": "洗完提醒",
    "salt_lack": "专用盐不足提醒",
    "brightener_lack": "漂洗剂不足提醒",
    "cleaningReminderStatus": "滤网清洁提醒",
    "sprayArmStopNoticeStatus": "喷淋臂停转提醒",
    "aiStatus": "AI识水",
    "hotWind": "热风烘干",
    "peakValleyElectricSwitch": "峰谷电开关",
}


FRIDGE_PROFILE = {
    "refrigeratorDoorStatus": {
        "display_name": "冷藏室门状态",
        "entity_options": {
            "device_class": BinarySensorDeviceClass.DOOR,
        },
    },
    "freezerDoorStatus": {
        "display_name": "冷冻室门状态",
        "entity_options": {
            "device_class": BinarySensorDeviceClass.DOOR,
        },
    },
    "refrigerator2DoorStatus": {
        "display_name": "冷藏室门2状态",
        "entity_options": {
            "device_class": BinarySensorDeviceClass.DOOR,
        },
    },
    "freezer2DoorStatus": {
        "display_name": "冷冻室门2状态",
        "entity_options": {
            "device_class": BinarySensorDeviceClass.DOOR,
        },
    },
    "refSterilizationForcedOff": {
        "display_name": "冷藏室关闭净化",
        "platform": Platform.BUTTON,
        "command_value": "true",
    },
    "intelligenceMode": {"display_name": "智能存储"},
    "vtRoom2TargetTempLevel": {"display_name": "婴爱空间"},
    "sharingElectricityEndTime": {
        "display_name": "分时用电谷段结束时间",
        "include_without_value": True,
        "platform": Platform.TIME,
    },
    "sharingElectricityStartTime": {
        "display_name": "分时用电谷段开始时间",
        "include_without_value": True,
        "platform": Platform.TIME,
    },
    "freezerTargetTempLevel": {
        "display_name": "冷冻室",
        "companion_select": True,
    },
    "refSterilizationForcedOn": {
        "display_name": "冷藏室开启净化",
        "platform": Platform.BUTTON,
        "command_value": "true",
    },
    "refrigeratorTargetTempLevel": {
        "display_name": "冷藏室",
        "companion_select": True,
    },
    "quickFreezingMode": {"display_name": "速冻"},
    "daypartingElectricityStatus": {"display_name": "分时用电"},
    "travelMode": {"display_name": "外出节能"},
}


_PROFILE_BY_PRODUCT = {
    "FA08JM001": DISHWASHER_PROFILE,
    "CWC10-B29BKU1": DISHWASHER_PROFILE,
    "B00Y10000": FRIDGE_PROFILE,
    "BCD-450WGCFDM4WNU1": FRIDGE_PROFILE,
}


def get_app_profile(product_code: str | None, product_name: str | None) -> dict:
    """Return the verified official App profile for a device."""
    return (
        _PROFILE_BY_PRODUCT.get(product_code)
        or _PROFILE_BY_PRODUCT.get(product_name)
        or {}
    )


def get_cloud_preferences(
    product_code: str | None,
    product_name: str | None,
) -> dict:
    """Return official App cloud preferences for a verified product."""
    profile = get_app_profile(product_code, product_name)
    if profile is DISHWASHER_PROFILE:
        return DISHWASHER_CLOUD_PREFERENCES
    return {}
