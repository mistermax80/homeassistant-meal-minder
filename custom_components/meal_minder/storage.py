from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import Meal


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

    async def async_add_meal(
        self,
        date: str,
        meal_type: str,
        items: list[str],
        meal_time: str = "12:00",
    ):
        meal = Meal.create(
            date=date,
            time=meal_time,
            meal_type=meal_type,
            items=items,
        )

        self.data.setdefault("meals", [])

        self.data["meals"].append(meal.to_dict())

        await self.async_save()

    async def async_remove_meal(
        self,
        meal_id: str,
    ) -> bool:

        meals = self.data.get("meals", [])

        original_count = len(meals)

        self.data["meals"] = [meal for meal in meals if meal.get("id") != meal_id]

        removed = len(self.data["meals"]) < original_count

        if removed:
            await self.async_save()

        return removed

    async def async_update_meal(
        self,
        meal_id: str,
        **updates,
    ) -> bool:

        allowed_fields = {
            "date",
            "time",
            "type",
            "items",
        }

        meals = self.data.get("meals", [])

        for meal in meals:
            if meal.get("id") == meal_id:

                for key, value in updates.items():
                    if key in allowed_fields and value is not None:
                        meal[key] = value

                await self.async_save()
                return True

        return False
