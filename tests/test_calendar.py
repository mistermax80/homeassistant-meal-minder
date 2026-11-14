"""Test calendar titles and preserve existing event and instance behavior."""

# These tests use the same standard-library runner as the existing suite.
# ruff: noqa: PT009

import copy
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation
from homeassistant.util import dt as dt_util

from custom_components.meal_minder import calendar
from custom_components.meal_minder.calendar import MealMinderCalendar


class CalendarTests(unittest.IsolatedAsyncioTestCase):
    """Cover both calendar paths with mocked per-instance storage."""

    async def asyncSetUp(self):
        """Use real HA translation loading with local integration discovery."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.hass = HomeAssistant(directory.name)
        self.hass.config.language = "it"
        integration = SimpleNamespace(
            file_path=Path(calendar.__file__).parent,
            has_translations=True,
            name="Meal Minder",
        )
        discovery = patch.object(
            translation,
            "async_get_integrations",
            new_callable=AsyncMock,
            return_value={"meal_minder": integration},
        )
        discovery.start()
        self.addCleanup(discovery.stop)
        previous_zone = dt_util.DEFAULT_TIME_ZONE
        self.zone = ZoneInfo("Europe/Rome")
        dt_util.set_default_time_zone(self.zone)
        self.addCleanup(dt_util.set_default_time_zone, previous_zone)
        self.now = datetime(2026, 11, 14, 10, tzinfo=self.zone)
        clock = patch.object(dt_util, "now", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def make_calendar(self, meals, entry_id="A"):
        """Create a calendar without loading platforms or persistent storage."""
        storage = SimpleNamespace(
            entry_id=entry_id,
            async_get_resolved_meals=AsyncMock(return_value=meals),
        )
        entity = MealMinderCalendar(
            storage, SimpleNamespace(entry_id=entry_id, title=entry_id)
        )
        entity.hass = self.hass
        return entity

    async def get_events(self, entity):
        """Query the public calendar API for the fixed local day."""
        return await entity.async_get_events(
            self.hass,
            self.now.replace(hour=0),
            self.now.replace(hour=23, minute=59),
        )

    async def test_titles_in_daily_and_range_events(self):
        """Translate all supported types while retaining legacy and custom titles."""
        cases = (
            ("breakfast", "🍳 Colazione"),
            ("morning_snack", "🍪 Spuntino mattutino"),
            ("lunch", "🍝 Pranzo"),
            ("afternoon_snack", "🍪 Spuntino pomeridiano"),
            ("dinner", "🍽 Cena"),
            ("evening_snack", "🍪 Spuntino serale"),
            ("snack", "🍪 Spuntino"),
            ("custom_meal", "custom_meal"),
        )
        for meal_type, expected in cases:
            with self.subTest(meal_type=meal_type):
                meal = {"id": "meal", "time": "12:00", "type": meal_type}
                entity = self.make_calendar([meal])
                await entity.async_update()
                self.assertEqual(entity.event.summary, expected)
                events = await self.get_events(entity)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].summary, expected)

    async def test_event_fields_and_source_data_are_preserved(self):
        """Keep UIDs, local times, descriptions, ordering, and original meal data."""
        meals = [
            {"id": "later", "time": "20:00", "type": "dinner"},
            {
                "id": "first",
                "time": "12:00",
                "type": "morning_snack",
                "items": ["Fruit", "Yogurt"],
                "preparation": {"offset": 60, "items": ["Prepare fruit"]},
                "custom": {"keep": True},
            },
        ]
        before = copy.deepcopy(meals)
        entity = self.make_calendar(meals)
        await entity.async_update()
        daily = entity.event
        self.assertEqual(daily.uid, "first")
        self.assertEqual(daily.description, "• Fruit\n• Yogurt")
        ranged = await self.get_events(entity)
        self.assertEqual(
            [event.uid for event in ranged],
            ["first_2026-11-14", "later_2026-11-14"],
        )
        self.assertEqual(
            ranged[0].description,
            "• Fruit\n• Yogurt\n\nPreparazione:\n• Prepare fruit",
        )
        self.assertEqual(ranged[1].description, "")
        for event in (daily, ranged[0]):
            self.assertEqual(event.start, self.now.replace(hour=12))
            self.assertEqual(event.end, event.start + timedelta(minutes=30))
            self.assertEqual(event.start.utcoffset(), timedelta(hours=1))
        self.assertEqual(meals, before)
        self.assertEqual(entity.unique_id, "A_calendar")

    async def test_empty_calendar(self):
        """An empty plan has no current event or queried events."""
        entity = self.make_calendar([])
        await entity.async_update()
        self.assertIsNone(entity.event)
        self.assertEqual(await self.get_events(entity), [])

    async def test_untranslated_language_keeps_type_codes(self):
        """Do not supply English titles when no language resource is available."""
        self.hass.config.language = "en"
        entity = self.make_calendar(
            [{"id": "meal", "time": "12:00", "type": "morning_snack"}]
        )
        await entity.async_update()
        self.assertEqual(entity.event.summary, "morning_snack")
        self.assertEqual((await self.get_events(entity))[0].summary, "morning_snack")

    async def test_missing_translation_keeps_type_code(self):
        """Missing keys retain the stored code instead of an embedded title."""
        entity = self.make_calendar(
            [{"id": "meal", "time": "12:00", "type": "morning_snack"}]
        )
        with patch.object(
            calendar, "async_get_translations", new_callable=AsyncMock, return_value={}
        ) as translations:
            await entity.async_update()
            self.assertEqual(entity.event.summary, "morning_snack")
            self.assertEqual(
                (await self.get_events(entity))[0].summary, "morning_snack"
            )
        self.assertEqual(translations.await_count, 2)
        translations.assert_awaited_with(self.hass, "it", "selector", {"meal_minder"})

    async def test_updates_and_queries_are_isolated_between_instances(self):
        """An update for A leaves B's storage and current event untouched."""
        a = self.make_calendar(
            [{"id": "shared", "time": "12:00", "type": "morning_snack"}]
        )
        b = self.make_calendar(
            [{"id": "shared", "time": "13:00", "type": "evening_snack"}], "B"
        )
        await a.async_update()
        await b.async_update()
        b_event = b.event
        a.storage.async_get_resolved_meals.reset_mock()
        b.storage.async_get_resolved_meals.reset_mock()
        a.async_write_ha_state = Mock()
        b.async_write_ha_state = Mock()
        update = SimpleNamespace(data={"entry_id": "A"})
        await a._handle_update(update)  # noqa: SLF001
        await b._handle_update(update)  # noqa: SLF001
        a.storage.async_get_resolved_meals.assert_awaited_once_with(self.now.date())
        b.storage.async_get_resolved_meals.assert_not_awaited()
        a.async_write_ha_state.assert_called_once_with()
        b.async_write_ha_state.assert_not_called()
        self.assertIs(b.event, b_event)
        self.assertEqual((await self.get_events(a))[0].summary, "🍪 Spuntino mattutino")
        self.assertEqual((await self.get_events(b))[0].summary, "🍪 Spuntino serale")
        self.assertEqual((a.unique_id, b.unique_id), ("A_calendar", "B_calendar"))
