"""Test grace periods without changing meal or preparation reminders."""

# Use the standard-library runner available in the project environment.
# ruff: noqa: PT009

import copy
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from custom_components.meal_minder import sensor


class NextMealGraceTests(unittest.IsolatedAsyncioTestCase):
    """Cover inclusive grace boundaries, day changes, and separate consumers."""

    def setUp(self):
        """Use Home Assistant's Rome timezone for each test."""
        previous_zone = dt_util.DEFAULT_TIME_ZONE
        self.zone = ZoneInfo("Europe/Rome")
        dt_util.set_default_time_zone(self.zone)
        self.addCleanup(dt_util.set_default_time_zone, previous_zone)
        self.noon = datetime(2026, 11, 14, 12, tzinfo=self.zone)

    def make_storage(self, meals, entry_id="A"):
        """Resolve only the explicitly supplied dates."""
        return SimpleNamespace(
            entry_id=entry_id,
            async_get_resolved_meals=AsyncMock(
                side_effect=lambda day: meals.get(day, [])
            ),
        )

    def meal(self, time, meal_type="lunch"):
        """Return a meal with attributes that must remain unchanged."""
        return {"time": time, "type": meal_type, "items": [meal_type]}

    async def test_future_exact_and_grace_boundaries(self):
        """Keep lunch through minute 60, then select the next future meal."""
        lunch, dinner = self.meal("12:00"), self.meal("20:00", "dinner")
        meals = {self.noon.date(): [dinner, lunch]}
        before = copy.deepcopy(meals)
        storage = self.make_storage(meals)
        for minutes in (-30, 0, 30, 60, 61):
            with (
                self.subTest(minutes=minutes),
                patch.object(
                    dt_util, "now", return_value=self.noon + timedelta(minutes=minutes)
                ),
            ):
                result = await sensor.find_next_meal(storage, grace_minutes=60)
                expected = lunch if minutes <= 60 else dinner
                self.assertIs(result["meal"], expected)
                self.assertEqual(result["datetime"].strftime("%H:%M"), expected["time"])
        self.assertEqual(meals, before)

    async def test_latest_started_meal_wins_over_earlier_meal_and_future(self):
        """The previous meal must not hide a meal that has already started."""
        first, second, future = (
            self.meal("12:00"),
            self.meal("12:30", "afternoon_snack"),
            self.meal("13:00"),
        )
        storage = self.make_storage({self.noon.date(): [future, second, first]})
        for minutes in (30, 45):
            with (
                self.subTest(minutes=minutes),
                patch.object(
                    dt_util, "now", return_value=self.noon + timedelta(minutes=minutes)
                ),
            ):
                result = await sensor.find_next_meal(storage, grace_minutes=60)
                self.assertIs(result["meal"], second)

    async def test_midnight_previous_day_and_newer_meal(self):
        """Retain yesterday's meal only while eligible and no newer meal started."""
        previous = self.meal("23:30", "evening_snack")
        breakfast = self.meal("08:00", "breakfast")
        midnight = self.noon.replace(hour=0) + timedelta(days=1)
        meals = {self.noon.date(): [previous], midnight.date(): [breakfast]}
        storage = self.make_storage(meals)
        for minutes, expected in ((0, previous), (30, previous), (31, breakfast)):
            with (
                self.subTest(minutes=minutes),
                patch.object(
                    dt_util, "now", return_value=midnight + timedelta(minutes=minutes)
                ),
            ):
                result = await sensor.find_next_meal(storage, grace_minutes=60)
                self.assertIs(result["meal"], expected)
                if expected is previous:
                    self.assertEqual(result["datetime"].date(), self.noon.date())
        newer = self.meal("00:10")
        meals[midnight.date()].append(newer)
        with patch.object(
            dt_util, "now", return_value=midnight + timedelta(minutes=20)
        ):
            self.assertIs(
                (await sensor.find_next_meal(storage, grace_minutes=60))["meal"], newer
            )

    async def test_default_search_remains_strictly_future(self):
        """Without explicit grace, skip exact and past meals."""
        lunch, dinner = self.meal("12:00"), self.meal("20:00", "dinner")
        storage = self.make_storage({self.noon.date(): [lunch, dinner]})
        for minutes in (0, 30, 60):
            with (
                self.subTest(minutes=minutes),
                patch.object(
                    dt_util, "now", return_value=self.noon + timedelta(minutes=minutes)
                ),
            ):
                self.assertIs((await sensor.find_next_meal(storage))["meal"], dinner)

    async def test_sensors_and_instances_search_independently(self):
        """Only Next Meal uses grace; IDs, attributes, and other entries persist."""
        lunch, dinner = self.meal("12:00"), self.meal("20:00", "dinner")
        storage = self.make_storage({self.noon.date(): [lunch, dinner]})
        other = self.make_storage(
            {self.noon.date(): [self.meal("15:00", "morning_snack")]}, "B"
        )
        entry = SimpleNamespace(entry_id="A")
        current = sensor.MealMinderNextMealSensor(storage, entry)
        reminder = sensor.MealMinderNextMealReminderSensor(storage, entry)
        other_sensor = sensor.MealMinderNextMealSensor(
            other, SimpleNamespace(entry_id="B")
        )
        with patch.object(
            dt_util, "now", return_value=self.noon + timedelta(minutes=30)
        ):
            await current.async_update()
            await reminder.async_update()
            await other_sensor.async_update()
        self.assertEqual(current.native_value, self.noon)
        self.assertEqual(
            current.extra_state_attributes, {"meal_type": "lunch", "items": ["lunch"]}
        )
        self.assertEqual(current.unique_id, "A_next_meal")
        self.assertEqual(reminder.native_value, self.noon.replace(hour=19))
        self.assertEqual(
            reminder.extra_state_attributes,
            {
                "meal_type": "dinner",
                "meal_time": "20:00",
                "items": ["dinner"],
                "datetime": self.noon.replace(hour=19).isoformat(),
            },
        )
        self.assertEqual(reminder.unique_id, "A_next_meal_reminder")
        self.assertEqual(other_sensor.native_value, self.noon.replace(hour=15))
        self.assertEqual(other_sensor.unique_id, "B_next_meal")

    async def test_no_eligible_meals(self):
        """Expired meals must not remain visible when no future meal exists."""
        storage = self.make_storage({self.noon.date(): [self.meal("12:00")]})
        with patch.object(
            dt_util, "now", return_value=self.noon + timedelta(minutes=61)
        ):
            self.assertIsNone(await sensor.find_next_meal(storage, grace_minutes=60))

    async def test_preparation_sensor_does_not_use_meal_grace_search(self):
        """Keep preparation selection independent of find_next_meal."""
        preparation = sensor.MealMinderNextPreparationReminderSensor(
            self.make_storage({}), SimpleNamespace(entry_id="A")
        )
        with (
            patch.object(sensor, "find_next_meal", new_callable=AsyncMock) as meals,
            patch.object(
                sensor,
                "find_next_preparation",
                new_callable=AsyncMock,
                return_value=None,
            ) as preparations,
        ):
            await preparation.async_update()
        meals.assert_not_awaited()
        preparations.assert_awaited_once_with(preparation.storage)
