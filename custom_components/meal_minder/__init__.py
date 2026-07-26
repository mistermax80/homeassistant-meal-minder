from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse

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

    hass.data.setdefault(
        DOMAIN,
        {},
    )

    hass.data[DOMAIN]["storage"] = storage

    async def create_plan(call: ServiceCall):

        plan = await storage.async_create_plan(
            name=call.data["name"],
            start_date=call.data["start_date"],
            end_date=call.data["end_date"],
        )

        return {
            "plan": plan,
        }

    async def add_meal(call: ServiceCall):

        await storage.async_add_meal(
            meal_type=call.data["meal_type"],
            items=[
                item.strip()
                for item in call.data.get(
                    "items",
                    "",
                ).splitlines()
                if item.strip()
            ],
            meal_time=str(
                call.data.get(
                    "time",
                    "12:00",
                )
            )[:5],
            weekday=call.data.get(
                "weekday",
            ),
            date=call.data.get(
                "date",
            ),
        )

        hass.bus.async_fire("meal_minder_updated")

    async def remove_meal(call: ServiceCall):

        removed = await storage.async_remove_meal(call.data["id"])

        if removed:
            hass.bus.async_fire("meal_minder_updated")

    async def update_meal(call: ServiceCall):

        data = call.data.copy()

        meal_id = data.pop("id")

        if "items" in data:

            data["items"] = [
                item.strip() for item in data["items"].splitlines() if item.strip()
            ]

        if "meal_type" in data:

            data["type"] = data.pop("meal_type")

        if "time" in data:

            data["time"] = str(data["time"])[:5]

        if "weekday" in data:

            data["weekday"] = int(data["weekday"])

        if data.get("clear_date"):
            data["date"] = None

        data.pop("clear_date", None)

        if data.get("clear_weekday"):
            data["weekday"] = None

        data.pop("clear_weekday", None)

        updated = await storage.async_update_meal(
            meal_id,
            **data,
        )

        if updated:

            hass.bus.async_fire("meal_minder_updated")

    async def get_meals(call: ServiceCall):

        meals = await storage.async_get_meals(
            date=call.data.get("date"),
            weekday=call.data.get("weekday"),
            meal_type=call.data.get("meal_type"),
        )

        return {
            "meals": meals,
        }

    hass.services.async_register(
        DOMAIN,
        "create_plan",
        create_plan,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        "add_meal",
        add_meal,
    )

    hass.services.async_register(
        DOMAIN,
        "remove_meal",
        remove_meal,
    )

    hass.services.async_register(
        DOMAIN,
        "update_meal",
        update_meal,
    )

    hass.services.async_register(
        DOMAIN,
        "get_meals",
        get_meals,
        supports_response=SupportsResponse.ONLY,
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True
