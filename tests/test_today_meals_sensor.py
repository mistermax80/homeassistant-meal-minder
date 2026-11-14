"""Test Today Meals against the installed Home Assistant APIs using unittest."""

# Ruff prefers pytest assertions, but these tests run with standard unittest.
# ruff: noqa: PT009

import copy
import tempfile
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers import event as event_helper
from homeassistant.util import dt as dt_util

from custom_components.meal_minder import sensor


class TodayMealsSensorTests(unittest.IsolatedAsyncioTestCase):
    """Cover sensor data, local scheduling, removal, and instance isolation."""

    async def asyncSetUp(self):
        """Create a real HA event loop context with mocked storage only."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.hass = HomeAssistant(directory.name)
        previous_zone = dt_util.DEFAULT_TIME_ZONE
        dt_util.set_default_time_zone(ZoneInfo("Europe/Rome"))
        self.addCleanup(dt_util.set_default_time_zone, previous_zone)
        self.instant = datetime(2026, 11, 14, 23, 30, tzinfo=UTC)
        clock = patch.object(
            dt_util, "now", side_effect=lambda: dt_util.as_local(self.instant)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def make_sensor(self, entry_id="A", meals=None):
        """Create an entity without loading unrelated integration platforms."""
        storage = SimpleNamespace(
            entry_id=entry_id,
            async_get_resolved_meals=AsyncMock(return_value=meals or []),
        )
        entity = sensor.MealMinderTodayMealsSensor(
            storage, SimpleNamespace(entry_id=entry_id, title=entry_id)
        )
        entity.hass = self.hass
        entity.entity_id = f"sensor.{entry_id.lower()}_today_meals"
        writer = patch.object(entity, "async_write_ha_state")
        writer.start()
        self.addCleanup(writer.stop)
        return entity

    async def test_local_date_and_meal_compatibility(self):
        """Use the HA date and preserve all meal data and sorting."""
        meals = [
            {
                "id": "dinner",
                "time": "20:00",
                "type": "dinner",
                "items": ["Fish"],
                "weekday": -1,
                "date": None,
                "preparation": {"offset": 120, "items": ["Defrost"]},
                "custom": {"keep": True},
            },
            {"id": "breakfast", "time": "08:00", "items": []},
        ]
        original = copy.deepcopy(meals)
        entity = self.make_sensor(meals=meals)
        await entity.async_update()
        self.assertEqual(entity.extra_state_attributes["date"], "2026-11-15")
        entity.storage.async_get_resolved_meals.assert_awaited_once_with(
            dt_util.as_local(self.instant).date()
        )
        self.assertEqual(entity.native_value, 2)
        self.assertEqual(entity.name, "Today Meals")
        self.assertEqual(entity.unique_id, "A_today_meals")
        self.assertTrue(entity.should_poll)
        self.assertEqual(entity.extra_state_attributes["meals"], [meals[1], meals[0]])
        self.assertIs(entity.extra_state_attributes["meals"][1], meals[0])
        self.assertEqual(meals, original)

    async def test_empty_day(self):
        """An empty day still exposes its date and a numeric zero."""
        entity = self.make_sensor()
        await entity.async_update()
        self.assertEqual(entity.native_value, 0)
        self.assertEqual(
            entity.extra_state_attributes, {"date": "2026-11-15", "meals": []}
        )

    async def test_midnight_refresh_with_unchanged_count(self):
        """Advance both date and attributes even when the meal count is unchanged."""
        entity = self.make_sensor(meals=[{"time": "12:00", "items": ["Old"]}])
        cancel = Mock()
        with patch.object(
            sensor, "async_track_time_change", autospec=True, return_value=cancel
        ) as track:
            await entity.async_added_to_hass()
            track.assert_called_once_with(
                self.hass, entity._handle_midnight, hour=0, minute=0, second=0  # noqa: SLF001
            )
            self.instant = datetime(2026, 11, 15, 23, 0, tzinfo=UTC)
            entity.storage.async_get_resolved_meals.return_value = [
                {"time": "12:00", "items": ["New"]}
            ]
            await track.call_args.args[1](dt_util.as_local(self.instant))
            self.assertEqual(entity.extra_state_attributes["date"], "2026-11-16")
            self.assertEqual(
                entity.extra_state_attributes["meals"][0]["items"], ["New"]
            )
            self.assertEqual(entity.native_value, 1)
            self.assertEqual(entity.async_write_ha_state.call_count, 2)
            await entity.async_remove()
        cancel.assert_called_once_with()

    async def test_real_scheduler_local_midnight_and_cancellation(self):
        """Check real HA timer targets over winter, summer, and DST transitions."""
        instants = [
            datetime(2026, 11, 14, 12, tzinfo=UTC),
            datetime(2026, 7, 14, 12, tzinfo=UTC),
            datetime(2026, 3, 29, 0, 30, tzinfo=UTC),
            datetime(2026, 10, 25, 0, 30, tzinfo=UTC),
        ]
        for instant in instants:
            with self.subTest(instant=instant):
                self.instant = instant
                entity = self.make_sensor()
                handles = []
                call_at = self.hass.loop.call_at

                def capture_timer(*args, call_at=call_at, handles=handles, **kwargs):
                    handle = call_at(*args, **kwargs)
                    handles.append(handle)
                    return handle

                with (
                    patch.object(dt_util, "utcnow", return_value=instant),
                    patch.object(
                        event_helper,
                        "async_track_point_in_utc_time",
                        wraps=event_helper.async_track_point_in_utc_time,
                    ) as point,
                    patch.object(self.hass.loop, "call_at", side_effect=capture_timer),
                ):
                    await entity.async_added_to_hass()
                    target = dt_util.as_local(point.call_args.args[2])
                    self.assertEqual(
                        (target.hour, target.minute, target.second), (0, 0, 0)
                    )
                    self.assertGreater(target.date(), dt_util.as_local(instant).date())
                    self.assertEqual(len(handles), 1)
                    self.assertFalse(handles[0].cancelled())
                    await entity.async_remove()
                    self.assertTrue(handles[0].cancelled())

    async def test_events_and_removal_are_isolated(self):
        """Use the real event bus and remove A without disrupting B."""
        a, b = self.make_sensor("A"), self.make_sensor("B")
        with patch.object(
            sensor,
            "async_track_time_change",
            autospec=True,
            side_effect=[Mock(), Mock()],
        ) as track:
            await a.async_added_to_hass()
            await b.async_added_to_hass()
            a.storage.async_get_resolved_meals.reset_mock()
            b.storage.async_get_resolved_meals.reset_mock()
            self.hass.bus.async_fire("meal_minder_updated", {"entry_id": "A"})
            await self.hass.async_block_till_done()
            a.storage.async_get_resolved_meals.assert_awaited_once()
            b.storage.async_get_resolved_meals.assert_not_awaited()
            await a.async_remove()
            a.storage.async_get_resolved_meals.reset_mock()
            self.hass.bus.async_fire("meal_minder_updated", {"entry_id": "A"})
            self.hass.bus.async_fire("meal_minder_updated", {"entry_id": "B"})
            self.hass.bus.async_fire("meal_minder_updated", {})
            await self.hass.async_block_till_done()
            a.storage.async_get_resolved_meals.assert_not_awaited()
            b.storage.async_get_resolved_meals.assert_awaited_once()
            await b.async_remove()
            self.assertEqual(track.call_count, 2)
