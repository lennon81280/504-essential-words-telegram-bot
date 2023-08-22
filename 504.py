import os
import random
import csv
import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

TOKEN = os.getenv("BOT_TOKEN")

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

def create_connection():
    return sqlite3.connect('words_database.db')

def start(update: Update, context: CallbackContext) -> None:
    custom_keyboard = [
        [KeyboardButton("Learn Word"), KeyboardButton("Progress")],
    ]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    update.message.reply_text("Tap 'Learn Word' to discover a new word or check your 'Progress'.", reply_markup=reply_markup)

def learn_word(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id

    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM learned_words WHERE chat_id = ?", (chat_id,))
        learned_words = [row[0] for row in cursor.fetchall()]

    with open('words.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header row

        available_words = [row for row in reader if row[1] not in learned_words]

        if available_words:
            selected_row = random.choice(available_words)
            word = selected_row[1]
            definition = selected_row[2]

            custom_keyboard = [
                [KeyboardButton("Got it ✅"), KeyboardButton("Shit, remind another time 🤦‍♂️")],
                [KeyboardButton(f"Show definition of '{word}' 👓")],
                [KeyboardButton("Learn another word 💡"), KeyboardButton("Progress")],
            ]
            reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

            context.user_data['current_word'] = word
            context.user_data['current_definition'] = definition

            response = f"Word: {word}"
            update.message.reply_text(response, reply_markup=reply_markup)
        else:
            update.message.reply_text("Congratulations! You've learned all available words.")

def got_it(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    word = context.user_data.get('current_word')
    if word:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO learned_words (chat_id, word) VALUES (?, ?)", (chat_id, word))
            conn.commit()
            context.user_data.pop('current_word', None)
            update.message.reply_text("OK ✅")

def show_progress(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id

    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT word) FROM learned_words WHERE chat_id = ?", (chat_id,))
        learned_count = cursor.fetchone()[0]

    total_words = 492
    progress_percent = (learned_count / total_words) * 100

    response = f"You've learned {learned_count} out of {total_words} words.\nProgress: {progress_percent:.2f}%"
    update.message.reply_text(response)


def remind_another_time(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("OK")

def learn_another_word(update: Update, context: CallbackContext) -> None:
    context.user_data.pop('current_word', None)
    learn_word(update, context)

def show_definition(update: Update, context: CallbackContext) -> None:
    definition = context.user_data.get('current_definition')
    if definition:
        response = f"Definition: {definition}"
        update.message.reply_text(response)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text("Learn Word"), learn_word))
    dp.add_handler(MessageHandler(Filters.text("Got it ✅"), got_it))
    dp.add_handler(MessageHandler(Filters.text("Shit, remind another time 🤦‍♂️"), remind_another_time))
    dp.add_handler(MessageHandler(Filters.text("Learn another word 💡"), learn_another_word))
    dp.add_handler(MessageHandler(Filters.text("Progress"), show_progress))
    dp.add_handler(MessageHandler(Filters.regex(r"^Show definition of"), show_definition))

    updater.start_polling(clean=True, timeout=10, read_latency=2.0)
    updater.idle()

if __name__ == '__main__':
    main()
