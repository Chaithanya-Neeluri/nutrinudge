
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import json
import random

app = FastAPI()

# Load recipe data
with open("weekly_recipe_nutrition (2).json") as f:
    recipes = json.load(f)

# Classify recipe into meal categories
def classify_meal_category(name):
    name = name.lower()
    if any(x in name for x in ["almond", "soaked", "jeera water", "herbal tea"]): return "pre_breakfast"
    if any(x in name for x in ["idli", "poha", "dosa", "paratha", "upma", "chilla", "breakfast", "oats"]): return "breakfast"
    if "salad" in name: return "salads"
    if any(x in name for x in ["banana", "apple", "papaya", "orange", "fruit", "mango"]): return "fruits"
    if any(x in name for x in ["dal", "rice", "roti", "sambar", "lunch", "pulao", "sabzi", "khichdi"]): return "lunch"
    if any(x in name for x in ["snack", "makhana", "sprout", "cutlet", "chana", "pakora"]): return "snacks"
    if any(x in name for x in ["dinner", "light", "soup", "khichdi", "chapati", "curry", "paneer"]): return "dinner"
    if any(x in name for x in ["milk", "turmeric", "post dinner", "warm water"]): return "post_dinner"
    return "misc"

# Classify all recipes
category_map = {}
for r in recipes:
    cat = classify_meal_category(r["recipe_name"])
    if cat not in category_map:
        category_map[cat] = []
    category_map[cat].append(r)

class UserInput(BaseModel):
    age: int
    gender: str
    height: float
    weight: float
    activity: str
    condition: str
    cuisine: str
    dislikes: List[str]
    allergies: List[str]
    food_preference: str
    nutrients: List[str]

def calculate_tdee(age, gender, weight, height, activity):
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if gender == "Male" else -161)
    multiplier = {
        "Sedentary": 1.2,
        "Lightly": 1.375,
        "Active": 1.55,
        "Very": 1.725
    }.get(activity, 1.2)
    return bmr * multiplier

def filter_by_condition(r, condition):
    name = r["recipe_name"].lower()
    if condition == "Diabetes":
        if "sugar" in name or "cake" in name or "kheer" in name or "dessert" in name or r.get("carbohydrate", 0) > 30:
            return False
    elif condition == "Hypertension":
        if "pickle" in name or "fried" in name or "papad" in name or r.get("fat", 0) > 25:
            return False
    elif condition == "Thyroid":
        if any(x in name for x in ["cabbage", "mustard", "broccoli"]):
            return False
    return True

def filter_by_preference(r, pref):
    name = r["recipe_name"].lower()
    if pref == "Vegetarian" and any(x in name for x in ["chicken", "egg", "meat", "fish"]):
        return False
    if pref == "Vegan" and any(x in name for x in ["milk", "curd", "cheese", "paneer", "ghee", "butter", "egg", "yogurt"]):
        return False
    if pref == "Keto" and r.get("carbohydrate", 0) > 15:
        return False
    if pref == "Millet-Based" and "millet" not in name:
        return False
    return True

def score_recipe(r, nutrients):
    score = 0
    if "Protein" in nutrients: score += r.get("protein", 0) * 1.5
    if "Iron" in nutrients: score += r.get("iron", 0) * 2.0
    if "Fibre" in nutrients: score += r.get("fibre", 0) * 1.5
    if "Calcium" in nutrients: score += r.get("calcium", 0) * 1.2
    return score

@app.post("/generate-plan")
def generate_plan(user: UserInput):
    tdee = calculate_tdee(user.age, user.gender, user.weight, user.height, user.activity)
    per_meal_target = tdee / 8

    # Apply all filters and scoring
    filtered_map = {}
    for cat, items in category_map.items():
        scored = []
        for r in items:
            name = r["recipe_name"].lower()
            if all(bad.lower() not in name for bad in user.dislikes + user.allergies):
                if filter_by_condition(r, user.condition) and filter_by_preference(r, user.food_preference):
                    if r.get("calories", 0) <= per_meal_target + 100:  # soft cap
                        r["score"] = score_recipe(r, user.nutrients)
                        scored.append(r)
        filtered_map[cat] = sorted(scored, key=lambda x: -x["score"])

    # Build weekly plan
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    meal_types = ["pre_breakfast", "breakfast", "salads", "fruits", "lunch", "snacks", "dinner", "post_dinner"]

    weekly_plan = {}
    for day in days:
        day_plan = {}
        for meal in meal_types:
            options = filtered_map.get(meal, [])
            if options:
                chosen = options.pop(0)
                day_plan[meal] = chosen
            else:
                day_plan[meal] = {"recipe_name": "No suitable recipe", "recipe_code": None}
        weekly_plan[day] = day_plan

    return {"status": "success", "tdee": round(tdee), "plan": weekly_plan}
