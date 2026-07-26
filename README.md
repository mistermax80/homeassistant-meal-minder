# 🍽️ Meal Minder

**Meal Minder** is a Home Assistant custom integration to manage meals and build a simple meal plan directly inside Home Assistant.

The goal is to keep meal planning simple and automation-friendly, using Home Assistant as the central platform for storage, calendar events and future notifications.

## ✨ Features (M0)

Current features:

* ✅ Add meals through Home Assistant services
* ✅ Persistent storage using Home Assistant storage
* ✅ Calendar entity integration
* ✅ Display meals with:
  * date
  * time
  * meal type
  * list of meal items
* ✅ Support for:
  * breakfast
  * lunch
  * dinner

Example calendar event:

```
20:00 🍽 Dinner

• Chicken
• Potatoes
• Salad
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
  items: |
    Chicken
    Potatoes
    Salad
```

Each line represents one meal item.

## 🗂️ Data model

Meals are stored locally using Home Assistant storage.

Example:

```json
{
  "id": "d665c637986d44a9a52c89b29b6a1cae",
  "date": "2026-07-26",
  "time": "20:00",
  "type": "dinner",
  "items": [
    "Chicken",
    "Potatoes",
    "Salad"
  ]
}
```

## 🚀 Roadmap

### M0 - Foundation

* [x] Integration setup
* [x] Persistent storage
* [x] Calendar entity
* [x] Add meal service
* [x] Meal items support
* [x] Calendar events with unique identifiers

### M1 - Meal management

* [ ] Edit meals
* [ ] Delete meals
* [ ] Weekly meal overview
* [ ] Better UI integration
* [ ] Real-time calendar updates

### M2 - Smart reminders

* [ ] Configurable reminders
* [ ] Advance notifications
* [ ] Preparation reminders

Example:

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