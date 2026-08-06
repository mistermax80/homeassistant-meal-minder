"""WebSocket API for Meal Minder."""

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN


def async_register(hass: HomeAssistant) -> None:
    """Register Meal Minder websocket commands."""

    websocket_api.async_register_command(
        hass,
        websocket_get_plans,
    )

    websocket_api.async_register_command(
        hass,
        websocket_get_plan,
    )

    websocket_api.async_register_command(
        hass,
        websocket_get_active_plan,
    )

    websocket_api.async_register_command(
        hass,
        websocket_get_meals,
    )

    websocket_api.async_register_command(
        hass,
        websocket_add_meal,
    )

    websocket_api.async_register_command(
        hass,
        websocket_update_meal,
    )

    websocket_api.async_register_command(
        hass,
        websocket_delete_meal,
    )


#
# GET PLANS
#


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/get_plans",
    }
)
@websocket_api.async_response
async def websocket_get_plans(
    hass: HomeAssistant,
    connection,
    msg,
):
    """Return all meal plans."""

    storage = _get_storage(hass, msg)

    plans = await storage.async_get_plans()

    connection.send_result(
        msg["id"],
        {
            "plans": plans,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/get_plan",
        vol.Required("plan_id"): cv.string,
    }
)
@websocket_api.async_response
async def websocket_get_plan(
    hass,
    connection,
    msg,
):
    """Get a single Meal Minder plan."""

    entry_id = next(iter(hass.data[DOMAIN]))

    storage = hass.data[DOMAIN][entry_id]

    plan = await storage.async_get_plan(msg["plan_id"])

    if plan is None:
        connection.send_error(
            msg["id"],
            "plan_not_found",
            "Meal plan not found",
        )
        return

    connection.send_result(
        msg["id"],
        {
            "plan": plan,
        },
    )


#
# GET ACTIVE PLAN
#


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/get_active_plan",
    }
)
@websocket_api.async_response
async def websocket_get_active_plan(
    hass: HomeAssistant,
    connection,
    msg,
):
    """Return active meal plan."""

    storage = _get_storage(hass, msg)

    plan = await storage.async_get_active_plan()

    connection.send_result(
        msg["id"],
        {
            "plan": plan,
        },
    )


#
# GET MEALS
#


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/get_meals",
        vol.Optional("date"): str,
        vol.Optional("weekday"): int,
        vol.Optional("meal_type"): str,
    }
)
@websocket_api.async_response
async def websocket_get_meals(
    hass: HomeAssistant,
    connection,
    msg,
):
    """Return meals."""

    storage = _get_storage(hass, msg)

    meals = await storage.async_get_meals(
        date=msg.get("date"),
        weekday=msg.get("weekday"),
        meal_type=msg.get("meal_type"),
    )

    connection.send_result(
        msg["id"],
        {
            "meals": meals,
        },
    )


#
# ADD MEAL
#


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/add_meal",
        vol.Required("plan_id"): str,
        vol.Required("meal_type"): str,
        vol.Required("items"): list,
        vol.Optional("time", default="12:00"): str,
        vol.Optional("weekday"): int,
        vol.Optional("date"): str,
    }
)
@websocket_api.async_response
async def websocket_add_meal(
    hass: HomeAssistant,
    connection,
    msg,
):
    """Add meal."""

    storage = _get_storage(hass, msg)

    await storage.async_add_meal(
        plan_id=msg["plan_id"],
        meal_type=msg["meal_type"],
        items=msg["items"],
        meal_time=msg["time"],
        weekday=msg.get("weekday"),
        date=msg.get("date"),
    )

    connection.send_result(
        msg["id"],
        {
            "success": True,
        },
    )


#
# UPDATE MEAL
#


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/update_meal",
        vol.Required("meal_id"): str,
        vol.Any(
            "date",
            "weekday",
            "time",
            "type",
            "items",
        ): object,
    }
)
@websocket_api.async_response
async def websocket_update_meal(
    hass: HomeAssistant,
    connection,
    msg,
):
    """Update meal."""

    storage = _get_storage(hass, msg)

    updates = {
        key: value
        for key, value in msg.items()
        if key
        in {
            "date",
            "weekday",
            "time",
            "type",
            "items",
        }
    }

    result = await storage.async_update_meal(
        msg["meal_id"],
        **updates,
    )

    connection.send_result(
        msg["id"],
        {
            "success": result,
        },
    )


#
# DELETE MEAL
#


@websocket_api.websocket_command(
    {
        vol.Required("type"): "meal_minder/delete_meal",
        vol.Required("meal_id"): str,
    }
)
@websocket_api.async_response
async def websocket_delete_meal(
    hass: HomeAssistant,
    connection,
    msg,
):
    """Delete meal."""

    storage = _get_storage(hass, msg)

    result = await storage.async_remove_meal(
        msg["meal_id"],
    )

    connection.send_result(
        msg["id"],
        {
            "success": result,
        },
    )


#
# STORAGE HELPER
#


def _get_storage(hass, msg):
    """Return Meal Minder storage instance."""

    entry_id = msg.get("entry_id")

    if not entry_id:
        # primo entry configurato
        entry_id = next(iter(hass.data[DOMAIN]))

    return hass.data[DOMAIN][entry_id]
