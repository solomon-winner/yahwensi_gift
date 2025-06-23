from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
import os
import random

# Database Setup
conn = sqlite3.connect("assignments.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        chosen_name TEXT,
        assigned_name TEXT,
        attempts INTEGER DEFAULT 0
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS assigned_names (
        name TEXT PRIMARY KEY
    )
''')
conn.commit()

# Names
name_list = [
    "solomon", "selam", "yididya", "eden", "bety tesfaye", "bety melese", "bernabas",
    "mntie", "frie", "aster ayana", "aster bekalu", "sami", "feven", "bemni", "elshu"
]

# Utilities
def get_user(user_id):
    cursor.execute("SELECT chosen_name, assigned_name, attempts FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def get_unassigned_names(exclude_name=None):
    cursor.execute("SELECT name FROM assigned_names")
    taken = [row[0] for row in cursor.fetchall()]
    return [name for name in name_list if name not in taken and name != exclude_name]

def assign_name(user_id, chosen_name):
    available = get_unassigned_names(exclude_name=chosen_name)
    if not available:
        return None
    assigned = random.choice(available)
    cursor.execute("INSERT INTO assigned_names (name) VALUES (?)", (assigned,))
    cursor.execute("INSERT INTO users (user_id, chosen_name, assigned_name, attempts) VALUES (?, ?, ?, 1)",
                   (user_id, chosen_name, assigned))
    conn.commit()
    return assigned

def increment_attempt(user_id):
    cursor.execute("UPDATE users SET attempts = attempts + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start", callback_data="start_process")]]
    await update.message.reply_text("Welcome ያህዌንሲ", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_data = get_user(user_id)
    if user_data:
        await query.edit_message_text(
            f"👋 Welcome back {user_data[0]}!\nYou're assigned to: {user_data[1]}\n(Shhh, keep it secret!)"
        )
        return

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"choose_{name}")]
        for name in name_list
    ]
    await query.edit_message_text("Click your name from the list:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chosen_name = query.data.replace("choose_", "")
    await query.answer()

    user_data = get_user(user_id)

    if user_data:
        _, assigned_name, attempts = user_data
        if attempts >= 2:
            await query.edit_message_text("❌ You have already tried twice. You cannot change again.")
            return
        increment_attempt(user_id)
        await query.edit_message_text(
            f"😯 Oh, you are {chosen_name}? How are you doing?\nYou were already assigned to: *{assigned_name}*\n(Still secret!)",
            parse_mode="Markdown"
        )
    else:
        assigned = assign_name(user_id, chosen_name)
        if not assigned:
            await query.edit_message_text("⚠️ Sorry, all names have been assigned or only your own name is left.")
            return
        await query.edit_message_text(
            f"🎉 Oooh you are *{chosen_name}*? How you doing?\n🎁 You are giving your gift to: *{assigned}*\n🤫 (Shhh... Keep it secret!)",
            parse_mode="Markdown"
        )

# Run Bot
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❗ Set BOT_TOKEN environment variable")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start_process, pattern="start_process"))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern="^choose_"))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
