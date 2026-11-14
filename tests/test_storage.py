"""Test meal scheduling writes and compatibility with historical storage."""

# These tests use unittest because pytest is not installed in the environment.
# ruff: noqa: PT009, PT027

import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from custom_components.meal_minder import storage as storage_module
from custom_components.meal_minder.const import DOMAIN

VALID_SCHEDULES = (
    {"weekday": -1},
    {"weekday": 0},
    {"weekday": 6},
    {"date": "2028-02-29"},
)
INVALID_SCHEDULES = (
    {},
    {"weekday": None, "date": None},
    {"weekday": 0, "date": "2026-11-14"},
    *({"weekday": value} for value in (True, False, -2, 7, "0", 0.0)),
    *(
        {"date": value}
        for value in (
            "",
            "2026-02-29",
            "20261114",
            "2026-W46-6",
            "2026-11-14T12:00:00",
            "2026-1-01",
            123,
        )
    ),
)


class StorageScheduleTests(unittest.IsolatedAsyncioTestCase):
    """Exercise public storage methods with disk I/O mocked at Store."""

    def make_storage(self, entry_id="A"):
        """Construct independent per-entry storage and an existing plan."""
        hass = Mock()
        with patch.object(storage_module, "Store", autospec=True) as store_factory:
            storage = storage_module.MealMinderStorage(hass, entry_id)
        storage.data = {
            "active_plan": "existing",
            "plans": [
                {
                    "id": "existing",
                    "name": "Existing",
                    "start_date": "2026-01-01",
                    "end_date": "2028-12-31",
                    "meals": [],
                }
            ],
        }
        store_factory.assert_called_once_with(
            hass, storage_module.STORAGE_VERSION, storage.storage_key
        )
        return storage

    async def add_meal(self, storage, **schedule):
        """Create a meal through the production public API."""
        await storage.async_add_meal("existing", "lunch", ["Food"], **schedule)
        return storage.data["plans"][0]["meals"][-1]

    def diet(self, meals):
        """Build an import payload that must not replace existing plans."""
        return {
            "name": "Diet",
            "start_date": "2026-01-01",
            "end_date": "2028-12-31",
            "meals": meals,
        }

    def diet_meal(self, **schedule):
        """Build a complete meal payload with the requested schedule."""
        return {"time": "12:00", "type": "lunch", "items": ["Food"], **schedule}

    async def test_creation_accepts_explicit_schedules(self):
        """Accept daily, weekday boundaries, and an exact leap-day date."""
        for schedule in VALID_SCHEDULES:
            with self.subTest(schedule=schedule):
                storage = self.make_storage()
                meal = await self.add_meal(storage, **schedule)
                self.assertEqual(meal["weekday"], schedule.get("weekday"))
                self.assertEqual(meal["date"], schedule.get("date"))
                storage.store.async_save.assert_awaited_once_with(storage.data)

    async def test_creation_rejects_invalid_schedules_without_writes(self):
        """Reject missing, conflicting, mistyped, or invalid schedules."""
        for schedule in INVALID_SCHEDULES:
            with self.subTest(schedule=schedule):
                storage = self.make_storage()
                before = copy.deepcopy(storage.data)
                with self.assertRaises(ValueError):
                    await self.add_meal(storage, **schedule)
                self.assertEqual(storage.data, before)
                storage.store.async_save.assert_not_awaited()

    async def test_partial_updates_preserve_schedule_and_switch_atomically(self):
        """Preserve omitted fields and support explicit schedule replacement."""
        storage = self.make_storage()
        meal = await self.add_meal(storage, weekday=0)
        self.assertTrue(await storage.async_update_meal(meal["id"], items=["Changed"]))
        self.assertEqual(meal["weekday"], 0)
        await storage.async_update_meal(meal["id"], weekday=None, date="2026-11-14")
        self.assertEqual((meal["weekday"], meal["date"]), (None, "2026-11-14"))
        await storage.async_update_meal(meal["id"], weekday=-1, date=None)
        self.assertEqual((meal["weekday"], meal["date"]), (-1, None))

    async def test_invalid_final_updates_do_not_mutate_any_field(self):
        """Validate the merged record before applying even unrelated changes."""
        storage = self.make_storage()
        meal = await self.add_meal(storage, weekday=0)
        for updates in (
            {"weekday": None},
            {"date": "2026-11-14"},
            {"weekday": True},
            {"weekday": 7},
        ):
            with self.subTest(updates=updates):
                before = copy.deepcopy(storage.data)
                storage.store.async_save.reset_mock()
                with self.assertRaises(ValueError):
                    await storage.async_update_meal(
                        meal["id"], items=["Rejected"], **updates
                    )
                self.assertEqual(storage.data, before)
                storage.store.async_save.assert_not_awaited()

    async def test_legacy_unrelated_edits_and_explicit_repair(self):
        """Keep absent/null schedules unchanged until explicitly repaired."""
        for schedule in ({}, {"weekday": None, "date": None}):
            with self.subTest(schedule=schedule):
                storage = self.make_storage()
                meal = {"id": "legacy", "time": "12:00", "items": [], **schedule}
                storage.data["plans"][0]["meals"].append(meal)
                await storage.async_update_meal(
                    "legacy", items=["Updated"], time="13:00"
                )
                self.assertEqual(
                    meal,
                    {"id": "legacy", "time": "13:00", "items": ["Updated"], **schedule},
                )
                before = copy.deepcopy(storage.data)
                with self.assertRaises(ValueError):
                    await storage.async_update_meal("legacy", weekday=None)
                self.assertEqual(storage.data, before)
                await storage.async_update_meal("legacy", weekday=-1)
                self.assertEqual(meal["weekday"], -1)

    async def test_diet_validation_finishes_before_plan_creation(self):
        """Reject a bad second meal without creating or saving any plan."""
        bad_meals = [self.diet_meal(**schedule) for schedule in INVALID_SCHEDULES]
        bad_meals.extend(
            [
                {"type": "lunch", "items": [], "weekday": -1},
                self.diet_meal(weekday=-1) | {"preparation": []},
            ]
        )
        for bad_meal in bad_meals:
            with self.subTest(meal=bad_meal):
                storage = self.make_storage()
                before = copy.deepcopy(storage.data)
                with patch.object(
                    storage, "async_create_plan", wraps=storage.async_create_plan
                ) as create:
                    with self.assertRaises(ValueError):
                        await storage.async_import_diet(
                            self.diet([self.diet_meal(weekday=-1), bad_meal])
                        )
                    create.assert_not_awaited()
                self.assertEqual(storage.data, before)
                storage.store.async_save.assert_not_awaited()

    async def test_valid_and_empty_diets_preserve_existing_plan(self):
        """Import new plans without replacing existing ones or changing active ID."""
        for meals in ([], [self.diet_meal(**schedule) for schedule in VALID_SCHEDULES]):
            with self.subTest(meals=meals):
                storage = self.make_storage()
                existing = copy.deepcopy(storage.data["plans"][0])
                plan = await storage.async_import_diet(self.diet(meals))
                self.assertEqual(storage.data["plans"][0], existing)
                self.assertEqual(storage.data["active_plan"], "existing")
                self.assertEqual(len(plan["meals"]), len(meals))
                self.assertEqual(len(storage.data["plans"]), 2)

    async def test_legacy_load_backup_and_duplication_preserve_schedules(self):
        """Read and restore incomplete historical records without migration."""
        storage = self.make_storage()
        legacy = [
            {"id": "missing", "time": "12:00", "type": "lunch", "items": []},
            {
                "id": "null",
                "time": "20:00",
                "type": "dinner",
                "items": [],
                "weekday": None,
                "date": None,
            },
        ]
        storage.data["plans"][0]["meals"] = legacy
        original = copy.deepcopy(storage.data)
        storage.store.async_load.return_value = copy.deepcopy(original)
        await storage.async_load()
        self.assertEqual(storage.data, original)
        backup = await storage.async_get_export_data()
        restored = self.make_storage("B")
        result = await restored.async_import_data(copy.deepcopy(backup))
        self.assertEqual(result, {"plans": 1})
        self.assertEqual(restored.data, original)
        restored.hass.bus.async_fire.assert_called_once_with(
            "meal_minder_updated", {"entry_id": "B"}
        )
        self.assertEqual(
            await restored.async_get_resolved_meals(date(2026, 11, 14)), []
        )
        duplicate = await restored.async_duplicate_plan("existing", "Copy")
        for old, new in zip(legacy, duplicate["meals"], strict=True):
            self.assertNotEqual(new["id"], old["id"])
            self.assertEqual(
                {k: v for k, v in new.items() if k != "id"},
                {k: v for k, v in old.items() if k != "id"},
            )
        self.assertEqual(storage.data, original)

    async def test_file_backup_restoration_preserves_legacy_records(self):
        """Keep the file-based restore path permissive too."""
        storage = self.make_storage()
        payload = {"plans": [{"id": "legacy", "meals": [{"id": "unscheduled"}]}]}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "import.json"
            source.write_text(json.dumps({"integration": DOMAIN, "data": payload}))
            storage.hass.config.path.side_effect = lambda name: str(
                Path(directory) / name
            )
            storage.hass.async_add_executor_job = AsyncMock(
                side_effect=lambda fn, *args: fn(*args)
            )
            result = await storage.async_import(str(source))
            self.assertTrue(Path(result["backup"]).exists())
        self.assertEqual(storage.data, payload)
        storage.hass.bus.async_fire.assert_called_once_with(
            "meal_minder_updated", {"entry_id": "A"}
        )

    async def test_instances_have_separate_keys_and_writes(self):
        """Identical plan IDs in different entries must remain independent."""
        a, b = self.make_storage("A"), self.make_storage("B")
        self.assertNotEqual(a.storage_key, b.storage_key)
        before_b = copy.deepcopy(b.data)
        meal = await self.add_meal(a, weekday=-1)
        await a.async_update_meal(meal["id"], weekday=6)
        self.assertEqual(b.data, before_b)
        b.store.async_save.assert_not_awaited()
        self.assertFalse(await b.async_update_meal(meal["id"], weekday=0))
