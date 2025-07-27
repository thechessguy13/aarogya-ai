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
            if user_input.lower() in ["quit", "exit","clear"]:
                print("Goodbye!")
                break

            system_prompt = (
                "You are a precise, instruction-following diet logging robot named Aarogya.\n\n"
                "**EXECUTE THIS WORKFLOW EXACTLY:**\n"
                "1.  For each food item, you **MUST** call the `search_food_database` tool.\n"
                "2.  **IF THE FOOD IS FOUND:** Immediately proceed to Step 4.\n"
                "3.  **IF THE FOOD IS NOT FOUND:**\n"
                "    a. Call `search_internet_for_nutrition_info` **ONCE AND ONLY ONCE**.\n"
                "    b. If the search fails or returns an error, your task for this item is **FAILED**. Report this failure in your final summary. **DO NOT PROCEED.**\n"
                "    c. If the search succeeds, parse the data and call `add_new_food_to_database`.\n"
                "4.  **FINAL ACTION - LOGGING:** After you have the nutritional data (from step 2 or 3c), your final action for that item is to call the `log_food_to_database` tool.\n\n"
                "**---CRITICAL INSTRUCTION: TASK COMPLETION---**\n"
                "The `log_food_to_database` tool is the **TERMINAL** step for any successful food item. The moment you call this tool, your work on that specific item is **100% COMPLETE.**\n"
                "After processing all items from the user's request (either by logging them or marking them as failed), your **ONLY** remaining task is to output a single, natural language summary to the user. The summary must include the macros of the food item. **YOUR FINAL RESPONSE MUST NOT CONTAIN ANY TOOL CALLS.**"
            )


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
            print(
                "Aarogya AI: I'm sorry, an unexpected error occurred. Please check the logs for details."
            )

    # Dispose of the engine connection pool
    await engine.dispose()
    logger.info("--- System Shutting Down ---")


if __name__ == "__main__":
    asyncio.run(main())
