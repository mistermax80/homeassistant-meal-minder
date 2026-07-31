"""Base entities for Meal Minder."""

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN


class MealMinderSensorEntity(SensorEntity):
    """Base sensor entity for Meal Minder."""

    def __init__(
        self,
        storage,
        entry,
    ):
        """Initialize the Meal Minder sensor entity."""
        self.storage = storage
        self.entry = entry

    @property
    def device_info(self):
        """Return device information for the entity."""
        return {
            "identifiers": {
                (
                    DOMAIN,
                    self.entry.entry_id,
                )
            },
            "name": self.entry.title,
            "manufacturer": "Meal Minder",
            "model": "Meal Planner",
        }
