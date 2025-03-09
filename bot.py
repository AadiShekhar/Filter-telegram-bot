import os
import re
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

TOKEN = os.getenv("TOKEN")

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()

    if re.fullmatch(r"\d+", text):
        update.message.reply_text(f"{text}.mp3")
    elif re.fullmatch(r"\d+\s*-\s*\d+", text):
        start, end = map(int, text.split('-'))
        if start <= end:
            files = " ".join([f"{i}.mp3" for i in range(start, end + 1)])
            update.message.reply_text(files)
        else:
            update.message.reply_text("Invalid range!")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
