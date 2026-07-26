from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


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
        description: str,
        meal_time: str = "12:00",
    ):
        self.data.setdefault("meals", [])

        # normalizza formato HH:MM
        if meal_time:
            meal_time = str(meal_time)[:5]

        self.data["meals"].append(
            {
                "date": date,
                "time": meal_time,
                "type": meal_type,
                "description": description,
            }
        )

        await self.async_save()