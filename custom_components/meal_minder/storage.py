from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import Meal, MealPlan
from datetime import datetime

import logging

_LOGGER = logging.getLogger(__name__)


class MealMinderStorage:

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
    ):

        self.entry_id = entry_id

        self.store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry_id}",
        )

        self.data = {}

    async def async_load(self):
        self.data = await self.store.async_load() or {}

    async def async_save(self):
        await self.store.async_save(self.data)

    async def async_create_plan(
        self,
        name: str,
        start_date: str,
        end_date: str,
    ) -> dict:

        plan = MealPlan.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

        self.data.setdefault("plans", [])

        self.data["plans"].append(plan.to_dict())

        self.data["active_plan"] = plan.id

        await self.async_save()

        return plan.to_dict()

    async def async_add_meal(
        self,
        plan_id: str,
        meal_type: str,
        items: list[str],
        meal_time: str = "12:00",
        weekday: int | None = None,
        date: str | None = None,
        preparation: dict | None = None,
    ):

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

        active_plan = self.data.get("active_plan")

        for plan in self.data.get("plans", []):

            if plan["id"] == active_plan:

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

        allowed_fields = {
            "date",
            "weekday",
            "time",
            "type",
            "items",
            "preparation",  
        }

        active_plan = self.data.get("active_plan")

        for plan in self.data.get("plans", []):

            if plan["id"] == active_plan:

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

        active_plan = self.data.get("active_plan")

        for plan in self.data.get("plans", []):

            if plan["id"] == active_plan:

                return plan.get("meals", [])

        return []

    async def async_get_resolved_meals(
        self,
        target_date,
    ) -> list[dict]:
        """
        Resolve meal rules for a specific date.

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
        start_date = datetime.fromisoformat(active_plan["start_date"]).date()

        end_date = datetime.fromisoformat(active_plan["end_date"]).date()

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

        active_plan = self.data.get("active_plan")

        for plan in self.data.get(
            "plans",
            [],
        ):

            if plan["id"] == active_plan:
                return plan

        return None

    async def async_get_plans(self) -> list[dict]:

        return self.data.get(
            "plans",
            [],
        )

    async def async_update_plan(
        self,
        plan_id: str,
        **updates,
    ) -> bool:

        allowed_fields = {
            "name",
            "start_date",
            "end_date",
        }

        for plan in self.data.get("plans", []):

            if plan["id"] == plan_id:

                for key, value in updates.items():

                    if key in allowed_fields and value is not None:
                        plan[key] = value

                await self.async_save()

                return True

        return False

    async def async_delete_plan(
        self,
        plan_id: str,
    ) -> bool:

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

        for plan in self.data.get("plans", []):

            if plan["id"] == plan_id:

                self.data["active_plan"] = plan_id

                await self.async_save()

                return True

        return False
