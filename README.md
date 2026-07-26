# 🍽️ Meal Minder

![Development Status](https://img.shields.io/badge/status-in%20development-orange)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5?logo=homeassistant)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python)
![License](https://img.shields.io/badge/license-GPLv3-green)

**Meal Minder** is a Home Assistant custom integration to manage meal plans, recurring diets and smart meal reminders.

> 🚧 This project is currently under active development.  
> Features, APIs and data models may change before the first stable release.

The goal is to transform meal planning into an automation engine integrated with Home Assistant.

Meal Minder is designed around:
- 📅 meal plans with start/end dates
- 🔁 recurring weekly meals
- 📌 date-based exceptions
- 🔔 future smart reminders
- 🛒 future shopping list integration

## 🧪 Current Status

The integration is currently usable for testing:

✅ Create meal plans  
✅ Add recurring meals  
✅ Add date exceptions  
✅ Update and remove meals  
✅ Query meals through services  

⚠️ Not yet recommended for production use.

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

## 🚀 Roadmap

### ✅ M0 - Foundation

- [x] Integration setup
- [x] Persistent storage
- [x] Calendar entity
- [x] Add meal service
- [x] Meal CRUD operations
- [x] MealPlan container
- [x] Weekly recurring meals
- [x] Date exceptions

### 🔄 M1 - Meal management (in progress)

- [ ] MealPlan CRUD
- [ ] Multiple diet plans
- [ ] Active plan selection
- [ ] Better calendar rendering
- [ ] Lovelace dashboard

### 🔔 M2 - Smart reminders

- [ ] Configurable reminders
- [ ] Preparation notifications
- [ ] Ingredient availability checks
- [ ] Example:
  
  > "Dinner tomorrow requires meat to be defrosted today at 15:00"

### 🧠 M3 - Advanced features

- [ ] Shopping list integration
- [ ] Recipe support
- [ ] Mobile companion integration
- [ ] AI assisted meal planning

## 🤝 Contributing

Contributions, ideas and suggestions are welcome.

## 📄 License

Meal Minder is released under the GNU General Public License v3.0.

Commercial use requires a separate agreement.