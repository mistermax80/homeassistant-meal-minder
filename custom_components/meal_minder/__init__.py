from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .storage import MealMinderStorage

PLATFORMS = [
    "calendar",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    storage = MealMinderStorage(hass)

    await storage.async_load()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["storage"] = storage

    async def add_meal(call: ServiceCall):

        await storage.async_add_meal(
            date=call.data["date"],
            meal_type=call.data["meal_type"],
            description=call.data["description"],
            meal_time=str(call.data.get("time", "12:00"))[:5],
        )

        hass.bus.async_fire("meal_minder_updated")

    hass.services.async_register(
        DOMAIN,
        "add_meal",
        add_meal,
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True
