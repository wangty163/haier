"""Tests for gas water heater capability metadata."""
import unittest

from homeassistant.const import Platform

from custom_components.haier.core.attribute import V1SpecAttributeParser


class GasWaterHeaterAttributeTest(unittest.TestCase):
    def test_global_temperature_capabilities_are_numeric(self):
        parser = V1SpecAttributeParser()
        for low, high, step in (("32", "60", "0.5"), (32, 60, 0.5)):
            with self.subTest(low=low, high=high, step=step):
                attributes = [
                    {"name": "outWaterTemp"},
                    {
                        "name": "targetTemp",
                        "valueRange": {
                            "type": "STEP",
                            "dataStep": {
                                "minValue": low,
                                "maxValue": high,
                                "step": step,
                            },
                        },
                    },
                    {"name": "totalUseGasL"},
                ]

                (heater,) = parser.parse_global(attributes)

                self.assertEqual(heater.platform, Platform.WATER_HEATER)
                self.assertEqual(
                    heater.options,
                    {
                        "min_temp": 32.0,
                        "max_temp": 60.0,
                        "target_temperature_step": 0.5,
                    },
                )
