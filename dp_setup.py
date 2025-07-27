import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


load_dotenv()

# --- Database Connection Details ---
# These should match the 'environment' section in your docker-compose.yml
DB_USER = os.getenv("POSTGRES_USER", "aarogya_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "strong_password_123")
DB_NAME = os.getenv("POSTGRES_DB", "aarogya_db")
DB_HOST = "localhost"
DB_PORT = "5432"

# The connection string for SQLAlchemy
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- SQL Schema Definition ---
# This is the schema we designed in our plan
SQL_SCHEMA = """
-- Drop existing tables to start fresh (optional, good for development)
DROP TABLE IF EXISTS daily_logs, indian_food_items, users CASCADE;

-- For storing user information
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    profile JSONB
);

-- Our master table for Indian food nutrition
CREATE TABLE indian_food_items (
    food_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    search_aliases TEXT[],
    serving_unit VARCHAR(20) NOT NULL,
    serving_weight_grams REAL NOT NULL,
    calories REAL,
    protein_grams REAL,
    carbs_grams REAL,
    fat_grams REAL
);

-- The main log for all user entries
CREATE TABLE daily_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    log_type VARCHAR(20) NOT NULL,
    log_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);
"""

def setup_database():
    """Connects to the database and executes the schema setup script."""
    try:
        print("Connecting to the database...")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("Connection successful. Setting up tables...")
            connection.execute(text("BEGIN;")) # Start a transaction
            connection.execute(text(SQL_SCHEMA))
            connection.execute(text("COMMIT;")) # Commit the transaction
            print("Tables created successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Database setup process finished.")

if __name__ == "__main__":
    setup_database()