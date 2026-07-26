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

        self.data.setdefault(
            "meals",
            []
        )

        self.data["meals"].append(
            meal.to_dict()
        )

        await self.async_save()