import operator
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from core.config import OPENAI_API_KEY, TAVILY_API_KEY
from core.logger import logger

from tools.food_tools import (
    search_food_database,
    log_food_to_database,
    add_new_food_to_database,
    search_internet_for_nutrition
)

class FoodAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]


if not OPENAI_API_KEY or not TAVILY_API_KEY:
    logger.error("API keys for OpenAI and Tavily not found. Please set them in your .env file.")
    raise ValueError("API keys for OpenAI and Tavily not found. Please set them in your .env file.")

tools = [
    search_food_database,
    log_food_to_database,
    add_new_food_to_database,
    search_internet_for_nutrition
]
# ToolNode is smart and will run async tools correctly
tool_node = ToolNode(tools)

model = ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=0, api_key=OPENAI_API_KEY)
model = model.bind_tools(tools)

async def call_model(state: FoodAgentState):
    """The primary node that calls the LLM asynchronously."""
    logger.info("Agent: Calling model...")
    response = await model.ainvoke(state["messages"])
    if response.tool_calls:
        logger.info(f"Agent: Model requested tool calls: {response.tool_calls}")
    return {"messages": [response]}

# --- Graph Definition ---
def build_agent_graph():
    workflow = StateGraph(FoodAgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        lambda x: "tools" if x["messages"][-1].tool_calls else END,
        {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "agent")

    # .compile() creates the runnable graph object
    return workflow.compile()