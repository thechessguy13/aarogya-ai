import asyncio
import json
from sqlalchemy import text, JSON
from langchain_core.tools import tool
from langchain_tavily import TavilySearch 
from pydantic import BaseModel, Field
from core.config import TAVILY_API_KEY
from tavily import TavilyClient
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
    logger.info(f"TOOL: Logging to DB: {quantity} {unit} of {item_name}")
    try:
        async with engine.begin() as connection:
            details = {
                "item_name": item_name, "quantity": quantity, "unit": unit,
                "calories": calories, "protein": protein, "carbs": carbs, "fat": fat
            }
            
            # THE FIX: We explicitly mark the 'details' parameter as being of the JSON type.
            # We also convert our dictionary to a JSON string before sending it.
            stmt = text("INSERT INTO daily_logs (user_id, log_type, details) VALUES (:user_id, 'food', :details)")
            stmt = stmt.bindparams(details=JSON()) # <-- This tells SQLAlchemy how to handle the parameter

            await connection.execute(
                stmt, 
                {
                    "user_id": 1, 
                    "details": json.dumps(details) # <-- Pass the data as a JSON string
                }
            )
        return f"Successfully logged {item_name} to the database."
    except Exception as e:
        logger.error(f"DATABASE ERROR in log_food_to_database: {e}", exc_info=True)
        return f"Error: Failed to log '{item_name}' to the database due to an internal error."


@tool(args_schema=AddFoodDBInput)
async def add_new_food_to_database(name: str, serving_unit: str, serving_weight_grams: float, calories: float, protein_grams: float, carbs_grams: float, fat_grams: float) -> str:
    """Adds a new, previously unknown food item and its nutritional information to the 'indian_food_items' master table. Use this tool to save new information you found online."""
    logger.info(f"TOOL: Adding new food to master DB: '{name}'")
    try:
        async with engine.begin() as connection:
            stmt = text("""
                INSERT INTO indian_food_items (name, serving_unit, serving_weight_grams, calories, protein_grams, carbs_grams, fat_grams)
                VALUES (:name, :serving_unit, :serving_weight_grams, :calories, :protein_grams, :carbs_grams, :fat_grams)
                ON CONFLICT (name) DO NOTHING;
            """)
            # This tool was already correct as it doesn't write JSON, but adding a try/except is good practice.
            await connection.execute(stmt, {
                "name": name, "serving_unit": serving_unit, "serving_weight_grams": serving_weight_grams,
                "calories": calories, "protein_grams": protein_grams, "carbs_grams": carbs_grams, "fat_grams": fat_grams
            })
        logger.info(f"Successfully added '{name}' to the master food database.")
        return f"Successfully added '{name}' to the master food database."
    except Exception as e:
        logger.error(f"DATABASE ERROR in add_new_food_to_database: {e}", exc_info=True)
        return f"Error: Failed to add '{name}' to the master food database due to an internal error."

# search_internet_tool = TavilySearch(max_results=3)
# search_internet_tool.name = "search_internet_for_nutrition"
# search_internet_tool.description = (
#     "Use this tool ONLY when you cannot find a food item in the local 'search_food_database'. "
#     "Search for specific queries like 'nutritional information for 1 katori of vegetable biryani' to get the best results. "
#     "The search result will be a text snippet. You must parse it to extract the required nutritional values."
# )



@tool
def search_internet_for_nutrition(food_name: str) -> str:
    """
    Use this tool ONLY when a food item is not found in the local database.
    It searches the internet synchronously and returns a formatted string of nutritional information.
    """
    logger.info(f"TOOL: Searching internet for '{food_name}' (synchronous call)...")
    
    if not TAVILY_API_KEY:
        logger.error("Tavily API key not configured.")
        return "Error: The internet search service is not configured."
    
    query = f"nutritional information for 1 serving of {food_name} with macros"
    logger.info(f"Constructed Tavily Query: '{query}'")
    
    try:
        # Initialize the synchronous client
        # The default timeout for the underlying HTTP client is 5 seconds.
        # We can be explicit if we want.
        client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # This is a standard, blocking function call.
        # The LangChain/LangGraph runner will place this call in a thread.
        search_results = client.search(query=query, search_depth="basic", max_results=3)
        
        results_list = search_results.get('results', [])
        
        if not results_list:
            logger.warning(f"Internet search for '{food_name}' yielded no results from Tavily.")
            return "No information found online."

        # Log metadata
        logger.info(f"Tavily search returned {len(results_list)} results. Logging raw metadata:")
        for i, result in enumerate(results_list):
            log_entry = { "result_index": i + 1, "url": result.get("url"), "content_snippet": result.get("content", "N/A")[:250] + "..." }
            logger.info(f"Tavily Result Metadata: {json.dumps(log_entry)}")
            
        # Format for LLM
        formatted_string = f"Search Results for '{food_name}':\n\n"
        for i, result in enumerate(results_list):
            formatted_string += f"--- Result {i+1} ---\nContent: {result.get('content', 'N/A')}\n\n"
        
        logger.info(f"Formatted internet search results for '{food_name}' prepared for LLM.")
        return formatted_string

    except Exception as e:
        # This will catch timeouts from the underlying httpx client, or any other API error.
        logger.error(f"An unexpected error occurred during synchronous Tavily search for '{food_name}': {e}", exc_info=True)
        return "Error: An unexpected error occurred with the internet search service."