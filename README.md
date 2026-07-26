# 🍽️ Meal Minder

**Meal Minder** is a Home Assistant custom integration to manage meals, create a weekly meal plan and receive smart reminders before cooking.

The goal is to transform meal planning into a simple automation system integrated with Home Assistant.

## ✨ Features (M0)

Current features:

* ✅ Add meals through Home Assistant services
* ✅ Persistent storage using Home Assistant storage
* ✅ Calendar entity integration
* ✅ Display meals with:

  * date
  * time
  * meal type
  * description
* ✅ Support for breakfast, lunch and dinner

Example:

```
20:00 🍽 Dinner

Chicken and potatoes
```

## 📦 Installation

### Manual installation

Copy the integration into your Home Assistant configuration:

```
config/
└── custom_components/
    └── meal_minder/
```

Restart Home Assistant.

### HACS

Coming soon.

## ⚙️ Services

### `meal_minder.add_meal`

Add a meal to the plan.

Example:

```yaml
action: meal_minder.add_meal
data:
  date: "2026-07-26"
  time: "20:00"
  meal_type: "dinner"
  description: "Chicken and potatoes"
```

## 🗂️ Data model

Meals are stored locally inside Home Assistant.

Example:

```json
{
  "date": "2026-07-26",
  "time": "20:00",
  "type": "dinner",
  "description": "Chicken and potatoes"
}
```

## 🚀 Roadmap

### M0 - Foundation

* [x] Integration setup
* [x] Persistent storage
* [x] Calendar entity
* [x] Add meal service

### M1 - Meal management

* [ ] Edit meals
* [ ] Delete meals
* [ ] Weekly meal overview
* [ ] Better UI integration

### M2 - Smart reminders

* [ ] Configurable reminders
* [ ] Advance notifications
* [ ] Preparation reminders
* [ ] Example:

  > "Dinner at 20:00 requires meat to be defrosted at 15:00"

### M3 - Advanced features

* [ ] Shopping list integration
* [ ] Recipe support
* [ ] Mobile companion integration
* [ ] AI assisted meal planning

## 🤝 Contributing

Contributions, ideas and suggestions are welcome.

## 📄 License

Meal Minder is released under the GNU General Public License v3.0.

Commercial use requires a separate agreement.
