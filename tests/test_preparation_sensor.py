"""Verify actual preparation timestamps, ordering, and DST arithmetic."""

# These regressions run with the available standard-library test runner.
# ruff: noqa: PT009

import copy
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from custom_components.meal_minder import sensor


class PreparationSensorTests(unittest.IsolatedAsyncioTestCase):
    """Exercise preparation selection separately from meal grace periods."""

    def setUp(self):
        """Use Rome as the HA timezone and restore it after each test."""
        previous_zone = dt_util.DEFAULT_TIME_ZONE
        self.zone = ZoneInfo("Europe/Rome")
        dt_util.set_default_time_zone(self.zone)
        self.addCleanup(dt_util.set_default_time_zone, previous_zone)
        self.now = datetime(2026, 11, 14, 10, tzinfo=self.zone)
        clock = patch.object(dt_util, "now", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def meal(self, time="20:00", offset=240):
        """Build a meal with the existing preparation representation."""
        return {
            "time": time,
            "type": "dinner",
            "items": ["Food"],
            "preparation": {"offset": offset, "items": ["Defrost"]},
        }

    def make_storage(self, meals, entry_id="A"):
        """Provide independent per-date meals without changing their contents."""
        return SimpleNamespace(
            entry_id=entry_id,
            async_get_resolved_meals=AsyncMock(
                side_effect=lambda day: meals.get(day, [])
            ),
        )

    async def test_offset_is_subtracted_without_mutating_meal(self):
        """20:00 minus 240 minutes must be exactly 16:00 local."""
        meal = self.meal()
        original = copy.deepcopy(meal)
        result = await sensor.find_next_preparation(
            self.make_storage({self.now.date(): [meal]})
        )
        self.assertEqual(result["datetime"].isoformat(), "2026-11-14T16:00:00+01:00")
        self.assertIs(result["meal"], meal)
        self.assertEqual(meal, original)

    async def test_tomorrows_meal_can_require_preparation_today(self):
        """Tomorrow 01:00 minus 180 minutes must be today 22:00."""
        tomorrow = self.now.date() + timedelta(days=1)
        result = await sensor.find_next_preparation(
            self.make_storage({tomorrow: [self.meal("01:00", 180)]})
        )
        self.assertEqual(result["datetime"].isoformat(), "2026-11-14T22:00:00+01:00")

    async def test_past_and_exact_preparations_are_ignored(self):
        """A passed or exact event must not linger through meal grace."""
        for hour in (16, 17):
            with self.subTest(hour=hour):
                self.now = self.now.replace(hour=hour)
                result = await sensor.find_next_preparation(
                    self.make_storage({self.now.date(): [self.meal()]})
                )
                self.assertIsNone(result)

    async def test_first_preparation_wins_even_when_meal_is_later(self):
        """Compare all events rather than selecting by meal time or list order."""
        later_meal = self.meal("20:00", 240)
        earlier_meal = self.meal("18:00", 60)
        result = await sensor.find_next_preparation(
            self.make_storage({self.now.date(): [earlier_meal, later_meal]})
        )
        self.assertIs(result["meal"], later_meal)
        self.assertEqual(result["datetime"].isoformat(), "2026-11-14T16:00:00+01:00")

    async def test_compare_preparations_across_meal_dates(self):
        """A later meal date can produce the earliest preparation event."""
        tomorrow = self.now.date() + timedelta(days=1)
        later_meal = self.meal("01:00", 600)
        result = await sensor.find_next_preparation(
            self.make_storage(
                {self.now.date(): [self.meal("20:00", 60)], tomorrow: [later_meal]}
            )
        )
        self.assertIs(result["meal"], later_meal)
        self.assertEqual(result["datetime"].isoformat(), "2026-11-14T15:00:00+01:00")

    async def test_zero_missing_offset_and_no_preparation(self):
        """Optional preparations remain optional and absent offset means zero."""
        for preparation in ({"offset": 0, "items": []}, {"items": []}):
            with self.subTest(preparation=preparation):
                meal = self.meal()
                meal["preparation"] = preparation
                result = await sensor.find_next_preparation(
                    self.make_storage({self.now.date(): [meal]})
                )
                self.assertEqual(
                    result["datetime"].isoformat(), "2026-11-14T20:00:00+01:00"
                )
        storage = self.make_storage(
            {
                self.now.date(): [
                    {"time": "12:00"},
                    {"time": "13:00", "preparation": None},
                ]
            }
        )
        self.assertIsNone(await sensor.find_next_preparation(storage))

    async def test_dst_changes_preserve_elapsed_offset_and_fold(self):
        """Subtract elapsed time across the missing and repeated local hour."""
        cases = [
            (
                datetime(2026, 3, 29, 0, tzinfo=self.zone),
                "2026-03-29T01:30:00+01:00",
                0,
            ),
            (
                datetime(2026, 10, 25, 0, tzinfo=self.zone),
                "2026-10-25T02:30:00+01:00",
                1,
            ),
        ]
        for now, expected, fold in cases:
            with self.subTest(now=now):
                self.now = now
                result = await sensor.find_next_preparation(
                    self.make_storage({now.date(): [self.meal("03:30", 60)]})
                )
                actual = result["datetime"]
                self.assertEqual(actual.isoformat(), expected)
                self.assertEqual(actual.fold, fold)
                meal_utc = now.replace(hour=3, minute=30).astimezone(UTC)
                self.assertEqual(
                    meal_utc - actual.astimezone(UTC), timedelta(minutes=60)
                )

    async def test_repeated_hour_uses_absolute_future_comparison(self):
        """02:30 CET is future even after 02:45 CEST on the same day."""
        self.now = datetime(2026, 10, 25, 2, 45, tzinfo=self.zone, fold=0)
        result = await sensor.find_next_preparation(
            self.make_storage({self.now.date(): [self.meal("03:30", 60)]})
        )
        self.assertEqual(result["datetime"].isoformat(), "2026-10-25T02:30:00+01:00")
        self.assertGreater(result["datetime"].astimezone(UTC), self.now.astimezone(UTC))

    async def test_sensor_attributes_and_instance_isolation(self):
        """Preserve sensor identity and attributes while keeping entries separate."""
        a = self.make_storage({self.now.date(): [self.meal()]}, "A")
        b = self.make_storage({self.now.date(): [self.meal("21:00", 60)]}, "B")
        first = sensor.MealMinderNextPreparationReminderSensor(
            a, SimpleNamespace(entry_id="A")
        )
        second = sensor.MealMinderNextPreparationReminderSensor(
            b, SimpleNamespace(entry_id="B")
        )
        await first.async_update()
        await second.async_update()
        self.assertEqual(first.native_value.isoformat(), "2026-11-14T16:00:00+01:00")
        self.assertEqual(second.native_value.isoformat(), "2026-11-14T20:00:00+01:00")
        self.assertEqual(first.unique_id, "A_next_preparation_reminder")
        self.assertEqual(second.unique_id, "B_next_preparation_reminder")
        self.assertEqual(
            first.extra_state_attributes,
            {
                "meal_type": "dinner",
                "meal_time": "20:00",
                "items": ["Defrost"],
                "datetime": "2026-11-14T16:00:00+01:00",
            },
        )
        first.async_write_ha_state = unittest.mock.Mock()
        await first._handle_update(SimpleNamespace(data={"entry_id": "B"}))  # noqa: SLF001
        first.async_write_ha_state.assert_not_called()
