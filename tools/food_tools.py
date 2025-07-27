import json
from sqlalchemy import text
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from pydantic import BaseModel, Field
from db.database import engine
from core.logger import logger

# --- Pydantic Schemas remain the same ---
class FoodSearchInput(BaseModel):
    food_name: str = Field(description="The name of the food item to search for.")

class AddFoodDBInput(BaseModel):
    name: str = Field(description="The name of the food item. E.g., 'Vegetable Biryani'")
    serving_unit: str = Field(description="The standard serving unit. E.g., 'katori', 'plate', 'piece'")
    serving_weight_grams: float = Field(description="The weight of one serving in grams.")
    calories: float = Field(description="Calories per serving.")
    protein_grams: float = Field(description="Grams of protein per serving.")
    carbs_grams: float = Field(description="Grams of carbohydrates per serving.")
    fat_grams: float = Field(description="Grams of fat per serving.")

# --- Tool Definitions are now async ---

@tool(args_schema=FoodSearchInput)
async def search_food_database(food_name: str) -> str:
    """
    Searches the local database for nutritional info of a given food item.
    This should be the FIRST tool you use for any food item.
    """
    logger.info(f"Searching local DB for '{food_name}'...")
    async with engine.connect() as connection:
        query = text("""
            SELECT name, serving_unit, serving_weight_grams, calories, protein_grams, carbs_grams, fat_grams
            FROM indian_food_items
            WHERE name ILIKE :name OR :name = ANY(search_aliases)
        """)
        result = await connection.execute(query, {"name": food_name})
        record = result.fetchone()

        if record:
            data = dict(record._mapping)
            logger.info(f"Found '{food_name}' in DB: {data}")
            return json.dumps(data)
        else:
            logger.warning(f"'{food_name}' not found in DB.")
            return json.dumps({"error": "Food item not found in the database. You may need to find it online."})

@tool
async def log_food_to_database(item_name: str, quantity: float, unit: str, calories: float, protein: float, carbs: float, fat: float) -> str:
    """Logs a consumed food item with its full nutritional details to the daily_logs table. Use this AFTER you have the nutritional info."""
    logger.info(f"Logging to DB: {quantity} {unit} of {item_name}")
    async with engine.begin() as connection:
        details = {
            "item_name": item_name, "quantity": quantity, "unit": unit,
            "calories": calories, "protein": protein, "carbs": carbs, "fat": fat
        }
        stmt = text("INSERT INTO daily_logs (user_id, log_type, details) VALUES (:user_id, 'food', :details::jsonb)")
        await connection.execute(stmt, {"user_id": 1, "details": json.dumps(details)})
    return f"Successfully logged {item_name} to the database."

@tool(args_schema=AddFoodDBInput)
async def add_new_food_to_database(name: str, serving_unit: str, serving_weight_grams: float, calories: float, protein_grams: float, carbs_grams: float, fat_grams: float) -> str:
    """Adds a new, previously unknown food item and its nutritional information to the 'indian_food_items' master table. Use this tool to save new information you found online."""
    logger.info(f"Adding new food to master DB: '{name}'")
    async with engine.begin() as connection:
        stmt = text("""
            INSERT INTO indian_food_items (name, serving_unit, serving_weight_grams, calories, protein_grams, carbs_grams, fat_grams)
            VALUES (:name, :serving_unit, :serving_weight_grams, :calories, :protein_grams, :carbs_grams, :fat_grams)
            ON CONFLICT (name) DO NOTHING;
        """)
        await connection.execute(stmt, {
            "name": name, "serving_unit": serving_unit, "serving_weight_grams": serving_weight_grams,
            "calories": calories, "protein_grams": protein_grams, "carbs_grams": carbs_grams, "fat_grams": fat_grams
        })
    return f"Successfully added '{name}' to the master food database."

search_internet_tool = TavilySearchResults(max_results=3)
search_internet_tool.name = "search_internet_for_nutrition"
search_internet_tool.description = (
    "Use this tool ONLY when you cannot find a food item in the local 'search_food_database'. "
    "Search for specific queries like 'nutritional information for 1 katori of vegetable biryani' to get the best results. "
    "The search result will be a text snippet. You must parse it to extract the required nutritional values."
)