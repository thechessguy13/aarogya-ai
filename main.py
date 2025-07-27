import asyncio
from sqlalchemy import text
from core.logger import logger
from db.database import engine, setup_database
from agents.food_agent import build_agent_graph
from langchain_core.messages import HumanMessage


async def main():
    """The main asynchronous entry point for the application."""
    logger.info("--- System Initializing ---")
    await setup_database()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (user_id, username) VALUES (1, 'test_user') ON CONFLICT (user_id) DO NOTHING;"
            )
        )

    app = build_agent_graph()

    print("\nAarogya AI is ready. How can I help you log your meals?")
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break

            system_prompt = """
            You are an expert Indian diet logging assistant named Aarogya.
            Your goal is to accurately log the user's food intake, learning about new foods when necessary.

            **Your Strict Workflow:**
            1.  For each food item the user mentions, you **MUST** first use the `search_food_database` tool.
            2.  **If the food is found in the database:** The tool will return its nutritional data. Proceed to step 5.
            3.  **If the food is NOT found in the database:**
                a. You **MUST** then use the `search_internet_for_nutrition` tool to find the information. Be specific in your search query (e.g., 'calories and macros for 1 plate of chole bhature').
                b. Carefully parse the text result from the internet search to extract the nutritional values (calories, protein, carbs, fat, serving size).
                c. If you successfully find the data online, you **MUST** immediately call the `add_new_food_to_database` tool to save this new knowledge permanently.
            4.  **If you cannot find the food in the database OR on the internet:** Inform the user that you were unable to find information for that specific item and cannot log it.
            5.  **Logging Step:** Once you have the nutritional information (either from the database or the internet), calculate the total nutrition based on the quantity the user mentioned (e.g., '2 samosas'). Then, you **MUST** call the `log_food_to_database` tool to record the entry in the user's daily log.
            6.  **Final Response:** After processing all items according to the workflow above, provide a single, final summary to the user about what was successfully logged (and from where) and what could not be found.
            """

            messages = [
                HumanMessage(content=f"{system_prompt}\n\nUser's meal: {user_input}")
            ]

            # Use ainvoke for async execution
            final_state = await app.ainvoke({"messages": messages})

            final_response = final_state["messages"][-1].content
            print(f"Aarogya AI: {final_response}")

        except KeyboardInterrupt:
            print("\nExiting application.")
            break

        except Exception:
            logger.exception("An unhandled error occurred in the main loop.")
            print("Aarogya AI: I'm sorry, an unexpected error occurred. Please check the logs for details.")

    # Dispose of the engine connection pool
    await engine.dispose()
    logger.info("--- System Shutting Down ---")



if __name__ == "__main__":
    asyncio.run(main())
    
