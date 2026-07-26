from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import Meal, MealPlan


class MealMinderStorage:

    def __init__(self, hass: HomeAssistant):
        self.store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
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
        meal_type: str,
        items: list[str],
        meal_time: str = "12:00",
        weekday: int | None = None,
        date: str | None = None,
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
        )

        active_plan_id = self.data.get("active_plan")

        if not active_plan_id:
            raise ValueError("No active meal plan")

        for plan in self.data.get("plans", []):

            if plan["id"] == active_plan_id:

                plan.setdefault("meals", [])

                plan["meals"].append(meal.to_dict())

                await self.async_save()

                return

        raise ValueError("Active meal plan not found")

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
