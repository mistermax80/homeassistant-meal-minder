"""Helper functions for Meal Minder."""

from .const import MEAL_TYPES, WEEKDAY_LABELS


def format_meal_label(meal: dict) -> str:
    """Format a meal for display in selectors."""

    if meal.get("date"):
        day_label = meal["date"]
    elif meal.get("weekday") is not None:
        day_label = WEEKDAY_LABELS[meal["weekday"]]

    meal_type = MEAL_TYPES.get(
        meal["type"],
        {
            "label": meal["type"].title(),
            "icon": "🍽",
        },
    )

    return f"{day_label} | {meal_type['icon']} {meal_type['label']} - {meal['time']}"


def meal_sort_key(meal: dict) -> tuple:
    """Sort meals for display."""

    if meal.get("date"):
        day_order = 99
    else:
        day_order = int(meal["weekday"])

    return (
        day_order,
        meal.get("date") or "",
        meal.get("time") or "00:00",
    )
