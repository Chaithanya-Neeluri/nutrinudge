from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import json
import random

app = FastAPI()

# Load recipe data - FIXED VERSION
with open("complete_structured_weekly_recipes.json") as f:
    data = json.load(f)

# Check if data is already categorized or needs to be processed
if isinstance(data, dict) and any(key in data for key in ["pre_breakfast", "breakfast", "lunch", "dinner"]):
    # Data is already categorized
    category_map = data
    # Flatten for backward compatibility if needed
    recipes = []
    for category, recipe_list in data.items():
        if isinstance(recipe_list, list):
            recipes.extend(recipe_list)
else:
    # Data is a flat list, needs categorization
    recipes = data
    # Classify recipe into meal categories
    def classify_meal_category(name):
        name = name.lower()
        if any(x in name for x in ["almond", "soaked", "jeera water", "herbal tea", "hot tea", "coffee", "espreso"]): 
            return "pre_breakfast"
        if any(x in name for x in ["idli", "poha", "dosa", "paratha", "upma", "chilla", "breakfast", "oats"]): 
            return "breakfast"
        if "salad" in name: 
            return "salads"
        if any(x in name for x in ["banana", "apple", "papaya", "orange", "fruit", "mango"]): 
            return "fruits"
        if any(x in name for x in ["dal", "rice", "roti", "sambar", "lunch", "pulao", "sabzi", "khichdi"]): 
            return "lunch"
        if any(x in name for x in ["snack", "makhana", "sprout", "cutlet", "chana", "pakora"]): 
            return "snacks"
        if any(x in name for x in ["dinner", "light", "soup", "khichdi", "chapati", "curry", "paneer"]): 
            return "dinner"
        if any(x in name for x in ["milk", "turmeric", "post dinner", "warm water"]): 
            return "post_dinner"
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
    if pref == "Vegetarian" and any(x in name for x in ["chicken", "egg", "meat", "fish", "mutton", "beef", "pork", "prawn", "crab", "seafood"]):
        return False
    if pref == "Non Vegetarian":
        # For non-vegetarian preference, we can include both veg and non-veg items
        # No filtering needed, accept all recipes
        return True
    if pref == "Vegan" and any(x in name for x in ["milk", "curd", "cheese", "paneer", "ghee", "butter", "egg", "yogurt", "honey", "chicken", "meat", "fish", "mutton", "beef", "pork", "prawn", "crab", "seafood"]):
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

def get_fallback_recipe(meal_type, all_recipes):
    """Get a default recipe for each meal type when no suitable recipe is found"""
    fallback_recipes = {
        "pre_breakfast": {
            "recipe_name": "Warm Water with Lemon",
            "recipe_code": "default_pre_breakfast",
            "calories": 5,
            "protein": 0,
            "carbohydrate": 1,
            "fat": 0,
            "fibre": 0,
            "iron": 0,
            "calcium": 2
        },
        "breakfast": {
            "recipe_name": "Basic Oats with Milk",
            "recipe_code": "default_breakfast",
            "calories": 150,
            "protein": 6,
            "carbohydrate": 25,
            "fat": 3,
            "fibre": 4,
            "iron": 1,
            "calcium": 120
        },
        "salads": {
            "recipe_name": "Mixed Green Salad",
            "recipe_code": "default_salad",
            "calories": 50,
            "protein": 2,
            "carbohydrate": 8,
            "fat": 1,
            "fibre": 3,
            "iron": 1,
            "calcium": 40
        },
        "fruits": {
            "recipe_name": "Seasonal Fresh Fruit",
            "recipe_code": "default_fruit",
            "calories": 80,
            "protein": 1,
            "carbohydrate": 20,
            "fat": 0,
            "fibre": 3,
            "iron": 0,
            "calcium": 15
        },
        "lunch": {
            "recipe_name": "Simple Dal Rice",
            "recipe_code": "default_lunch",
            "calories": 300,
            "protein": 12,
            "carbohydrate": 55,
            "fat": 4,
            "fibre": 8,
            "iron": 3,
            "calcium": 50
        },
        "snacks": {
            "recipe_name": "Handful of Mixed Nuts",
            "recipe_code": "default_snack",
            "calories": 120,
            "protein": 4,
            "carbohydrate": 6,
            "fat": 10,
            "fibre": 2,
            "iron": 1,
            "calcium": 30
        },
        "dinner": {
            "recipe_name": "Light Vegetable Soup",
            "recipe_code": "default_dinner",
            "calories": 100,
            "protein": 3,
            "carbohydrate": 15,
            "fat": 2,
            "fibre": 4,
            "iron": 1,
            "calcium": 25
        },
        "post_dinner": {
            "recipe_name": "Warm Turmeric Milk",
            "recipe_code": "default_post_dinner",
            "calories": 80,
            "protein": 4,
            "carbohydrate": 8,
            "fat": 3,
            "fibre": 0,
            "iron": 0,
            "calcium": 120
        }
    }
    
    return fallback_recipes.get(meal_type, fallback_recipes["snacks"])

@app.get("/")
def read_root():
    return {"message": "Nutrition API is running!", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "total_recipes": len(recipes)}

@app.post("/generate-plan")
def generate_plan(user: UserInput):
    try:
        tdee = calculate_tdee(user.age, user.gender, user.weight, user.height, user.activity)
        per_meal_target = tdee / 8

        # Apply all filters and scoring
        filtered_map = {}
        for cat, items in category_map.items():
            if not isinstance(items, list):
                continue
                
            scored = []
            for r in items:
                # Ensure recipe has required fields
                if not isinstance(r, dict) or "recipe_name" not in r:
                    continue
                    
                name = r["recipe_name"].lower()
                if all(bad.lower() not in name for bad in user.dislikes + user.allergies):
                    if filter_by_condition(r, user.condition) and filter_by_preference(r, user.food_preference):
                        if r.get("calories", 0) <= per_meal_target + 100:  # soft cap
                            r["score"] = score_recipe(r, user.nutrients)
                            scored.append(r.copy())  # Make a copy to avoid modifying original
            filtered_map[cat] = sorted(scored, key=lambda x: -x["score"])

        # Build weekly plan
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        meal_types = ["pre_breakfast", "breakfast", "salads", "fruits", "lunch", "snacks", "dinner", "post_dinner"]

        weekly_plan = {}
        used_recipes = {}  # Track used recipes per category to avoid repetition
        
        for day in days:
            day_plan = {}
            for meal in meal_types:
                available_recipes = filtered_map.get(meal, [])
                
                # Initialize used_recipes for this meal type if not exists
                if meal not in used_recipes:
                    used_recipes[meal] = set()
                
                # Find unused recipes first
                unused_recipes = [r for r in available_recipes if r.get("recipe_code") not in used_recipes[meal]]
                
                if unused_recipes:
                    # Use the highest scored unused recipe
                    chosen = unused_recipes[0]
                    used_recipes[meal].add(chosen.get("recipe_code"))
                    day_plan[meal] = chosen
                elif available_recipes:
                    # If all recipes are used, reset and reuse from the beginning
                    if len(used_recipes[meal]) >= len(available_recipes):
                        used_recipes[meal] = set()
                    
                    chosen = random.choice(available_recipes)
                    used_recipes[meal].add(chosen.get("recipe_code"))
                    day_plan[meal] = chosen
                else:
                    # No suitable recipes found, use fallback
                    day_plan[meal] = get_fallback_recipe(meal, category_map)
                    
            weekly_plan[day] = day_plan

        return {"status": "success", "tdee": round(tdee), "plan": weekly_plan}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Add CORS middleware if needed for Flutter app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
