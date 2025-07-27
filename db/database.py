import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from core.config import DATABASE_URL
from core.logger import logger

# Create an asynchronous engine
engine = create_async_engine(DATABASE_URL)

async def setup_database():
    """Connects to the database and ensures all tables are created asynchronously."""
    try:
        async with engine.begin() as conn:
            logger.info("Database connection successful. Ensuring schema exists...")

            await conn.run_sync(lambda sync_conn: sync_conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    profile JSONB
                );
            """)))

            await conn.run_sync(lambda sync_conn: sync_conn.execute(text("""
                CREATE TABLE IF NOT EXISTS indian_food_items (
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
            """)))

            await conn.run_sync(lambda sync_conn: sync_conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_logs (
                    log_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                    log_type VARCHAR(20) NOT NULL,
                    log_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    details JSONB
                );
            """)))

        logger.info("Schema verified/created successfully.")
    except Exception as e:
        logger.exception(f"An error occurred during database setup: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(setup_database())