from __future__ import annotations

from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class Meal:
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
        weekday: int | None = None,
        date: str | None = None,
        preparation=None,
    ) -> Meal:

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
    ) -> Meal:

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

        data = asdict(self)

        data["type"] = data.pop(
            "meal_type"
        )

        return data


@dataclass
class MealPlan:

    id: str
    name: str

    start_date: str
    end_date: str

    meals: list[Meal] = field(
        default_factory=list
    )

    @classmethod
    def create(
        cls,
        name: str,
        start_date: str,
        end_date: str,
    ) -> MealPlan:

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
    ) -> MealPlan:

        return cls(
            id=data["id"],
            name=data["name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            meals=[
                Meal.from_dict(meal)
                for meal in data.get("meals", [])
            ],
        )

    def add_meal(
        self,
        meal: Meal,
    ):

        self.meals.append(
            meal
        )

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "meals": [
                meal.to_dict()
                for meal in self.meals
            ],
        }