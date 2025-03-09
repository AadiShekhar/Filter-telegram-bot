import os
import re
import logging
import psycopg
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to PostgreSQL
def get_db_connection():
    return psycopg.connect(DATABASE_URL)

# Initialize DB Table
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT UNIQUE NOT NULL,
                    file_id TEXT NOT NULL
                )
            """)
            conn.commit()

# Save file to DB
def save_file(file_name, file_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO files (file_name, file_id) VALUES (%s, %s) ON CONFLICT (file_name) DO NOTHING", 
                        (file_name.lower(), file_id))
            conn.commit()

# Fetch file from DB
def get_file(file_name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT file_id FROM files WHERE file_name = %s", (file_name.lower(),))
            result = cur.fetchone()
            return result[0] if result else None

async def handle_audio(update: Update, context: CallbackContext):
    """Save uploaded .mp3 file details"""
    file = update.message.audio or update.message.document
    if file and file.mime_type == "audio/mpeg":
        file_name = file.file_name.lower()  # Ensure lowercase storage
        file_id = file.file_id
        save_file(file_name, file_id)
        logger.info(f"Saved file: {file_name} (ID: {file_id})")
        await update.message.reply_text(f"Saved {file_name}!")

async def handle_message(update: Update, context: CallbackContext):
    """Respond with the requested .mp3 file"""
    text = update.message.text.strip()
    logger.info(f"Received message: {text}")

    # If user sends just a number, assume it's an mp3 request
    if re.fullmatch(r"\d+", text):
        text += ".mp3"

    if re.fullmatch(r"\d+\.mp3", text):
        file_id = get_file(text)
        if file_id:
            logger.info(f"Sending file: {text}")
            await update.message.reply_audio(file_id)
        else:
            logger.warning(f"File {text} not found.")
            await update.message.reply_text("File not found.")

    elif re.fullmatch(r"\d+\s*-\s*\d+", text):
        start, end = map(int, text.split('-'))
        if start <= end:
            files = [f"{i}.mp3" for i in range(start, end + 1)]
            found = False
            for file_name in files:
                file_id = get_file(file_name)
                if file_id:
                    found = True
                    logger.info(f"Sending file: {file_name}")
                    await update.message.reply_audio(file_id)
            if not found:
                logger.warning("No files found in this range.")
                await update.message.reply_text("No files found in this range.")
        else:
            logger.warning("Invalid range entered.")
            await update.message.reply_text("Invalid range!")

def main():
    init_db()  # Ensure the database is initialized

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.AUDIO | filters.Document.MimeType("audio/mpeg"), handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running with polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
