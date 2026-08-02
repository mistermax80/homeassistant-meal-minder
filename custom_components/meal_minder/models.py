"""Data models used by Meal Minder."""

import uuid
from dataclasses import asdict, dataclass, field


@dataclass
class Meal:
    """Represent a meal entry used by Meal Minder."""

    id: str
    time: str
    meal_type: str
    items: list[str] = field(default_factory=list)
    # ricorrenza settimanale
    weekday: int | None = None
    # eccezione su giorno specifico
    date: str | None = None
    preparation: dict | None = None

    @classmethod
    def create(
        cls,
        time: str,
        meal_type: str,
        items: list[str],
        *,
        weekday: int | None = None,
        date: str | None = None,
        preparation=None,
    ) -> "Meal":
        """Create a new meal entry with a generated ID.

        Parameters
        ----------
        time : str
            The scheduled time for the meal.
        meal_type : str
            The type of meal (for example, breakfast, lunch, dinner).
        items : list[str]
            The items included in the meal.
        weekday : int | None, optional
            The weekday index for recurring meals, by default None.
        date : str | None, optional
            A specific date override for the meal, by default None.
        preparation : dict | None, optional
            Preparation details for the meal, by default None.

        Returns:
        -------
        Meal
            The created Meal instance.

        """

        return cls(
            id=uuid.uuid4().hex,
            time=time,
            meal_type=meal_type,
            items=items,
            weekday=weekday,
            date=date,
            preparation=preparation,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "Meal":
        """Create a Meal instance from a dictionary."""

        return cls(
            id=data["id"],
            time=data["time"],
            meal_type=data["type"],
            items=data.get("items", []),
            weekday=data.get("weekday"),
            date=data.get("date"),
            preparation=data.get("preparation"),
        )

    def to_dict(self) -> dict:
        """Convert the Meal instance to a dictionary suitable for storage."""

        data = asdict(self)

        data["type"] = data.pop("meal_type")

        return data


@dataclass
class MealPlan:
    """Represent a meal plan containing multiple Meal entries.

    Attributes:
    ----------
    id : str
        Unique identifier for the meal plan.
    name : str
        Human-readable name for the meal plan.
    start_date : str
        The start date for the meal plan (ISO format).
    end_date : str
        The end date for the meal plan (ISO format).
    meals : list[Meal]
        The list of meals included in this plan.

    """

    id: str
    name: str

    start_date: str
    end_date: str

    meals: list[Meal] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        name: str,
        start_date: str,
        end_date: str,
    ) -> "MealPlan":
        """Create a new MealPlan with a generated ID.

        Parameters
        ----------
        name : str
            Human-readable name for the meal plan.
        start_date : str
            The start date for the meal plan (ISO format).
        end_date : str
            The end date for the meal plan (ISO format).

        Returns:
        -------
        MealPlan
            The created MealPlan instance.

        """

        return cls(
            id=uuid.uuid4().hex,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "MealPlan":
        """Create a MealPlan instance from a dictionary."""

        return cls(
            id=data["id"],
            name=data["name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            meals=[Meal.from_dict(meal) for meal in data.get("meals", [])],
        )

    def to_dict(self) -> dict:
        """Convert the MealPlan instance to a dictionary suitable for storage."""

        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "meals": [meal.to_dict() for meal in self.meals],
        }
