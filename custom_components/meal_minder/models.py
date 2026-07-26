from __future__ import annotations

from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class Meal:
    id: str
    date: str
    time: str
    meal_type: str
    items: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        date: str,
        time: str,
        meal_type: str,
        items: list[str],
    ) -> Meal:

        return cls(
            id=uuid.uuid4().hex,
            date=date,
            time=time,
            meal_type=meal_type,
            items=items,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> Meal:

        return cls(
            id=data["id"],
            date=data["date"],
            time=data["time"],
            meal_type=data["type"],
            items=data["items"],
        )

    def to_dict(self) -> dict:

        data = asdict(self)

        data["type"] = data.pop(
            "meal_type"
        )

        return data


@dataclass
class MealPlan:
    meals: list[Meal] = field(
        default_factory=list
    )