import os
import re
import json
from telegram import Update, InputFile
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

TOKEN = os.getenv("TOKEN")
DATA_FILE = "files.json"  # File to store uploaded .mp3 files

# Load stored files
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        file_data = json.load(f)
else:
    file_data = {}

def save_data():
    """Save file data to JSON"""
    with open(DATA_FILE, "w") as f:
        json.dump(file_data, f)

def handle_audio(update: Update, context: CallbackContext):
    """Save uploaded .mp3 file details"""
    file = update.message.audio or update.message.document
    if file and file.mime_type == "audio/mpeg":
        file_name = file.file_name
        file_id = file.file_id
        file_data[file_name] = file_id
        save_data()
        update.message.reply_text(f"Saved {file_name}!")

def handle_message(update: Update, context: CallbackContext):
    """Respond with the requested .mp3 file"""
    text = update.message.text.strip()

    # Single file request
    if re.fullmatch(r"\d+\.mp3", text):
        if text in file_data:
            update.message.reply_audio(file_data[text])
        else:
            update.message.reply_text("File not found.")

    # Range request
    elif re.fullmatch(r"\d+\s*-\s*\d+", text):
        start, end = map(int, text.split('-'))
        if start <= end:
            found_files = [f"{i}.mp3" for i in range(start, end + 1) if f"{i}.mp3" in file_data]
            if found_files:
                for file in found_files:
                    update.message.reply_audio(file_data[file])
            else:
                update.message.reply_text("No files found in this range.")
        else:
            update.message.reply_text("Invalid range!")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.audio | Filters.document, handle_audio))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
