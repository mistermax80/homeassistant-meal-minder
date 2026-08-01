"""Storage management for Meal Minder."""

import json
import logging
import uuid
from datetime import date, datetime
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EXPORT_FILENAME,
    EXPORT_VERSION,
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)
from .exceptions import InvalidDateError, InvalidDateRangeError, PlanNotFoundError
from .models import Meal, MealPlan

_LOGGER = logging.getLogger(__name__)


def _normalize_plan_date(value: str | date | datetime | None) -> str | None:
    """Normalize a plan date to an ISO string."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def _parse_plan_date(value: str | date | datetime) -> date:
    """Parse a stored plan date into a date object."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return datetime.fromisoformat(str(value)).date()


class MealMinderStorage:
    """Manage persistent storage for Meal Minder integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
    ):
        """Initialize MealMinder storage for a config entry."""

        self.hass = hass
        self.entry_id = entry_id

        self.storage_key = f"{STORAGE_KEY}_{entry_id}"

        self.store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry_id}",
        )

        self.data = {}

    async def async_load(self):
        """Load Meal Minder storage data from disk."""
        self.data = await self.store.async_load() or {}

    async def async_save(self):
        """Save Meal Minder storage data to disk."""
        await self.store.async_save(self.data)

    async def async_create_plan(
        self,
        name: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Create a new meal plan and save it to storage."""

        start_date = _normalize_plan_date(start_date)
        end_date = _normalize_plan_date(end_date)

        if start_date is None or end_date is None:
            raise InvalidDateError

        if _parse_plan_date(end_date) <= _parse_plan_date(start_date):
            raise InvalidDateRangeError

        plan = MealPlan.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

        self.data.setdefault("plans", [])

        self.data["plans"].append(plan.to_dict())

        await self.async_save()

        return plan.to_dict()

    async def async_add_meal(
        self,
        plan_id: str,
        meal_type: str,
        items: list[str],
        *,
        meal_time: str = "12:00",
        weekday: int | None = None,
        date: str | None = None,
        preparation: dict | None = None,
    ) -> None:
        """Add a meal to an existing meal plan.

        Parameters
        ----------
        plan_id : str
            Identifier of the plan to add the meal to.
        meal_type : str
            Type of meal to add.
        items : list[str]
            Items included in the meal.
        meal_time : str, optional
            Scheduled time for the meal, by default "12:00".
        weekday : int | None, optional
            Weekday index for recurring meals, by default None.
        date : str | None, optional
            Specific date for the meal, by default None.
        preparation : dict | None, optional
            Preparation details for the meal, by default None.

        Raises:
        ------
        ValueError
            If both weekday and date are provided or the plan is not found.

        """

        # Meal can be added in three ways:
        # - weekday valorizzato
        # - date valorizzata
        # - entrambi null = tutti i giorni

        if weekday is not None and date is not None:
            raise ValueError("Meal cannot have both weekday and date")

        meal = Meal.create(
            time=meal_time,
            meal_type=meal_type,
            items=items,
            weekday=weekday,
            date=date,
            preparation=preparation,
        )

        for plan in self.data.get("plans", []):
            if plan["id"] == plan_id:
                plan.setdefault("meals", [])

                plan["meals"].append(meal.to_dict())

                await self.async_save()

                return

        raise ValueError(f"Meal plan {plan_id} not found")

    async def async_remove_meal(
        self,
        meal_id: str,
    ) -> bool:
        """Remove a meal from the meal plans.

        Parameters
        ----------
        meal_id : str
            The unique identifier of the meal to remove.

        Returns:
        -------
        bool
            True if a meal was removed, False otherwise.

        """

        for plan in self.data.get("plans", []):
            meals = plan.get("meals", [])

            original_count = len(meals)

            plan["meals"] = [meal for meal in meals if meal.get("id") != meal_id]

            removed = len(plan["meals"]) < original_count

            if removed:
                await self.async_save()

            return removed

        return False

    async def async_update_meal(
        self,
        meal_id: str,
        **updates,
    ) -> bool:
        """Update a meal with the provided changes.

        Parameters
        ----------
        meal_id : str
            The unique identifier of the meal to update.
        **updates
            Fields to update on the meal. Allowed fields are
            date, weekday, time, type, items, and preparation.

        Returns:
        -------
        bool
            True if the meal was found and updated, False otherwise.

        """

        allowed_fields = {
            "date",
            "weekday",
            "time",
            "type",
            "items",
            "preparation",
        }

        for plan in self.data.get("plans", []):
            for meal in plan.get("meals", []):
                if meal.get("id") == meal_id:
                    for key, value in updates.items():
                        if key in allowed_fields:
                            meal[key] = value

                    await self.async_save()

                    return True

        return False

    async def async_get_active_meals(
        self,
    ) -> list[dict]:
        """Return meals from the currently active meal plan."""

        active_plan = self.data.get("active_plan")

        for plan in self.data.get("plans", []):
            if plan["id"] == active_plan:
                return plan.get("meals", [])

        return []

    async def async_get_resolved_meals(
        self,
        target_date,
    ) -> list[dict]:
        """Resolve meal rules for a specific date.

        Priority:
        1. Exact date meals (exceptions)
        2. Weekday recurring meals
        3. Meals without date/weekday (every day)
        """

        active_plan_id = self.data.get("active_plan")

        _LOGGER.debug(
            "Active plan id: %s",
            active_plan_id,
        )

        if not active_plan_id:
            return []

        active_plan = None

        for plan in self.data.get("plans", []):
            if plan["id"] == active_plan_id:
                active_plan = plan
                break

        if not active_plan:
            return []

        _LOGGER.debug(
            "Target date: %s weekday=%s",
            target_date,
            target_date.weekday(),
        )

        # Check plan validity
        start_date = _parse_plan_date(active_plan["start_date"])

        end_date = _parse_plan_date(active_plan["end_date"])

        if not (start_date <= target_date <= end_date):
            return []

        resolved = []

        weekday = target_date.weekday()

        _LOGGER.debug(
            "Checking %s meals for %s",
            len(active_plan.get("meals", [])),
            target_date,
        )

        for meal in active_plan.get(
            "meals",
            [],
        ):
            # Exact date exception
            if meal.get("date"):
                if meal["date"] == target_date.isoformat():
                    resolved.append(meal)

                continue

            # Weekly recurring meal
            if meal.get("weekday") is not None:
                if meal["weekday"] == weekday:
                    resolved.append(meal)

                continue

            # Every day meal
            resolved.append(meal)

        return resolved

    async def async_get_meals(
        self,
        date: str | None = None,
        weekday: int | None = None,
        meal_type: str | None = None,
    ):
        """Return active meals filtered by date, weekday, and type.

        Parameters
        ----------
        date : str | None, optional
            ISO-formatted date to filter meals by exact date.
        weekday : int | None, optional
            Weekday index to filter recurring meals.
        meal_type : str | None, optional
            Meal type to filter returned meals.

        Returns:
        -------
        list[dict]
            Filtered list of active meal entries.

        """

        meals = await self.async_get_active_meals()

        if date is not None:
            meals = [meal for meal in meals if meal.get("date") == date]

        if weekday is not None:
            meals = [meal for meal in meals if meal.get("weekday") == weekday]

        if meal_type is not None:
            meals = [meal for meal in meals if meal.get("type") == meal_type]

        return meals

    async def async_get_active_plan(
        self,
    ) -> dict | None:
        """Return the active plan if one is set.

        Returns:
        -------
        dict | None
            The active plan dictionary, or None if not found.

        """

        active_plan = self.data.get("active_plan")

        for plan in self.data.get(
            "plans",
            [],
        ):
            if plan["id"] == active_plan:
                return plan

        return None

    async def async_get_plans(self) -> list[dict]:
        """Return all stored plans.

        Returns:
        -------
        list[dict]
            List of plan dictionaries.

        """

        return self.data.get(
            "plans",
            [],
        )

    async def async_update_plan(
        self,
        plan_id: str,
        **updates,
    ) -> bool:
        """Update a stored plan.

        Parameters
        ----------
        plan_id : str
            The ID of the plan to update.
        **updates
            Fields to update on the plan. Only "name", "start_date", and
            "end_date" are allowed.

        Returns:
        -------
        bool
            True if the plan was found and updated, False otherwise.

        """

        allowed_fields = {
            "name",
            "start_date",
            "end_date",
        }

        for plan in self.data.get("plans", []):
            if plan["id"] == plan_id:
                for key, value in updates.items():
                    if key in allowed_fields and value is not None:
                        if key in {"start_date", "end_date"}:
                            plan[key] = _normalize_plan_date(value)
                        else:
                            plan[key] = value

                if plan.get("start_date") and plan.get("end_date"):
                    if _parse_plan_date(plan["end_date"]) < _parse_plan_date(
                        plan["start_date"]
                    ):
                        raise InvalidDateRangeError

                await self.async_save()

                return True

        return False

    async def async_delete_plan(
        self,
        plan_id: str,
    ) -> bool:
        """Delete a plan from storage.

        Parameters
        ----------
        plan_id : str
            The ID of the plan to delete.

        Returns:
        -------
        bool
            True if the plan was deleted, False otherwise.

        """

        plans = self.data.get(
            "plans",
            [],
        )

        original_count = len(plans)

        self.data["plans"] = [plan for plan in plans if plan["id"] != plan_id]

        deleted = len(self.data["plans"]) < original_count

        if deleted:
            if self.data.get("active_plan") == plan_id:
                self.data["active_plan"] = None

            await self.async_save()

        return deleted

    async def async_set_active_plan(
        self,
        plan_id: str,
    ) -> bool:
        """Set the active plan.

        Parameters
        ----------
        plan_id : str
            The ID of the plan to activate.

        Returns:
        -------
        bool
            True if the plan was activated, False otherwise.

        """

        for plan in self.data.get("plans", []):
            if plan["id"] == plan_id:
                self.data["active_plan"] = plan_id

                await self.async_save()

                return True

        return False

    async def async_duplicate_plan(
        self,
        plan_id: str,
        name: str,
    ):
        """Duplicate an existing meal plan."""

        source = None

        for plan in self.data.get("plans", []):
            if plan["id"] == plan_id:
                source = plan
                break

        if source is None:
            raise PlanNotFoundError

        duplicated = {
            "id": uuid.uuid4().hex,
            "name": name,
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "meals": [],
        }

        for meal in source.get("meals", []):
            new_meal = meal.copy()
            new_meal["id"] = uuid.uuid4().hex
            duplicated["meals"].append(new_meal)

        self.data.setdefault(
            "plans",
            [],
        ).append(duplicated)

        await self.async_save()

        return duplicated

    async def async_export(self):
        """Export the current configuration to a JSON file.

        Returns:
        -------
        str
            The file path where the export was saved.

        """

        # data = await self.store.async_load()

        export_data = self._build_export_data()

        timestamp = dt_util.now().replace(microsecond=0).isoformat()

        filename = EXPORT_FILENAME.format(timestamp=timestamp)

        path = self.hass.config.path(filename)

        await self.hass.async_add_executor_job(
            self._write_export_file,
            path,
            export_data,
        )

        return path

    def _write_export_file(self, path, data):

        with Path(path).open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

    def _build_export_data(self):
        return {
            "integration": DOMAIN,
            "version": STORAGE_VERSION,
            "minor_version": STORAGE_MINOR_VERSION,
            "export_date": dt_util.now().isoformat(),
            "export_version": EXPORT_VERSION,
            "source_storage_key": self.storage_key,
            "data": self.data,
        }

    async def async_import(self, path: str):
        """Import meal minder data from a JSON export file.

        Parameters
        ----------
        path : str
            Path to the JSON export file.

        Raises:
        ------
        FileNotFoundError
            If the import file does not exist.
        HomeAssistantError
            If the file is not a JSON export file.
        ValueError
            If the file contents are not a valid Meal Minder export.

        """

        import_path = Path(path)

        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {path}")

        if import_path.suffix.lower() != ".json":
            raise HomeAssistantError("Only JSON export files are supported")
        #
        # Lettura file non bloccante
        #
        content = await self.hass.async_add_executor_job(
            import_path.read_text,
            "utf-8",
        )

        export_data = json.loads(content)

        #
        # Validazione integrazione
        #
        if export_data.get("integration") != DOMAIN:
            raise ValueError("Invalid Meal Minder export file")

        #
        # Validazione versione export
        #
        export_version = export_data.get(
            "export_version",
            1,
        )

        if export_version > 1:
            raise ValueError(f"Unsupported export version {export_version}")

        #
        # Recupero dati
        #
        imported_data = export_data.get("data")

        if not imported_data:
            raise ValueError("Missing data section")

        if "plans" not in imported_data:
            raise ValueError("Invalid meal plan data")

        #
        # Backup prima dell'import
        #
        backup_data = self._build_export_data()

        timestamp = dt_util.now().replace(microsecond=0).isoformat()

        filename = EXPORT_FILENAME.format(timestamp=timestamp)

        backup_path = self.hass.config.path(filename)

        await self.hass.async_add_executor_job(
            self._write_export_file,
            backup_path,
            backup_data,
        )

        #
        # Import dati nuovi
        #
        self.data = imported_data

        await self.store.async_save(self.data)

        #
        # Aggiorna sensori/calendari
        #
        self.hass.bus.async_fire("meal_minder_updated", {"entry_id": self.entry_id})

        return {
            "backup": str(backup_path),
            "plans": len(self.data.get("plans", [])),
        }
