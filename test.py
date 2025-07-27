import os
from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    print("Error: TAVILY_API_KEY not found in .env file.")
else:
    print("Tavily API key loaded. Attempting to connect...")
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        # Use a simple, common query
        query = "what is the capital of India"
        print(f"Sending query: '{query}'")
        
        # This is a blocking call
        response = client.search(query=query)
        
        print("\n--- SUCCESS ---")
        print("Successfully received a response from Tavily API.")
        print(response)

    except Exception as e:
        print("\n--- FAILURE ---")
        print(f"An error occurred while trying to connect to Tavily API: {e}")
        