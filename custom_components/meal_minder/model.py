from dataclasses import dataclass


@dataclass
class Meal:
    date: str
    meal_type: str
    description: str


@dataclass
class MealPlan:
    meals: list[Meal]