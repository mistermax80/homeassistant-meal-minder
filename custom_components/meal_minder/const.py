"""Constants for Meal Minder."""

DOMAIN = "meal_minder"

STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 1
STORAGE_KEY = "meal_minder_data"

EXPORT_VERSION = 1
EXPORT_FILENAME = "meal_minder_export_{timestamp}.json"


MEAL_TYPES = {
    "breakfast": {
        "label": "Breakfast",
        "icon": "🍳",
    },
    "snack": {
        "label": "Snack",
        "icon": "🥪",
    },
    "lunch": {
        "label": "Lunch",
        "icon": "🍝",
    },
    "dinner": {
        "label": "Dinner",
        "icon": "🍽",
    },
}

MEAL_TYPE_VALUES = tuple(MEAL_TYPES.keys())

MEAL_TYPE_ORDER = {
    "breakfast": 0,
    "snack": 1,
    "lunch": 2,
    "dinner": 3,
}

WEEKDAY_LABELS = {
    -1: "Every day",
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}
