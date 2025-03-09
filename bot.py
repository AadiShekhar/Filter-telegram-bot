import os
import re
import json
import logging
import asyncpg
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize database connection (global variable)
db_pool = None

async def init_db():
    """Initialize database connection pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id SERIAL PRIMARY KEY,
                file_name TEXT UNIQUE NOT NULL,
                file_id TEXT NOT NULL
            );
        """)
        logger.info("Database initialized.")

async def save_file(file_name, file_id):
    """Save file details in PostgreSQL."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO files (file_name, file_id) VALUES ($1, $2) ON CONFLICT (file_name) DO NOTHING",
            file_name, file_id
        )

async def get_file(file_name):
    """Retrieve file_id from database."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT file_id FROM files WHERE file_name = $1", file_name)
        return result

async def get_files_in_range(start, end):
    """Retrieve all file_ids in a given range."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT file_name, file_id FROM files WHERE file_name BETWEEN $1 AND $2", f"{start}.mp3", f"{end}.mp3")
        return {row["file_name"]: row["file_id"] for row in rows}

async def handle_audio(update: Update, context: CallbackContext):
    """Save uploaded .mp3 file details to database."""
    file = update.message.audio or update.message.document
    if file and file.mime_type == "audio/mpeg":
        file_name = file.file_name
        file_id = file.file_id

        await save_file(file_name, file_id)
        logger.info(f"Saved file: {file_name} (ID: {file_id})")
        await update.message.reply_text(f"Saved {file_name}!")

async def handle_message(update: Update, context: CallbackContext):
    """Respond with the requested .mp3 file"""
    text = update.message.text.strip()
    logger.info(f"Received message: {text}")

    # Single file request
    if re.fullmatch(r"\d+\.mp3", text):
        file_id = await get_file(text)
        if file_id:
            logger.info(f"Found file: {text}, sending...")
            await update.message.reply_audio(file_id)
        else:
            logger.warning(f"File {text} not found.")
            await update.message.reply_text("File not found.")

    # Range request
    elif re.fullmatch(r"\d+\s*-\s*\d+", text):
        start, end = map(int, text.split('-'))
        if start <= end:
            files = await get_files_in_range(start, end)
            if files:
                for file_name, file_id in files.items():
                    logger.info(f"Sending file: {file_name}")
                    await update.message.reply_audio(file_id)
            else:
                logger.warning("No files found in this range.")
                await update.message.reply_text("No files found in this range.")
        else:
            logger.warning("Invalid range entered.")
            await update.message.reply_text("Invalid range!")

async def main():
    """Start the bot with polling"""
    global db_pool
    await init_db()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.AUDIO | filters.Document.MimeType("audio/mpeg"), handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running with polling...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
