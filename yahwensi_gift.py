from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
import os

# ---- Setup Database ----
conn = sqlite3.connect("assignments.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    chosen_name TEXT,
    assigned_name TEXT,
    attempts INTEGER DEFAULT 0
)
""")
conn.commit()

# ---- Configurable Lists ----
user_names = ["Solomon", "Eyasu", "Sara", "Mimi", "Lomi"]
assignable_names = ["Selam", "Peace", "Hope", "Grace", "Light"]

# ---- Utility Functions ----
def get_available_assignable():
    cursor.execute("SELECT assigned_name FROM users")
    taken = [row[0] for row in cursor.fetchall()]
    return [name for name in assignable_names if name not in taken]

def assign_to_user(user_id, chosen_name):
    available = get_available_assignable()
    if not available:
        return None
    assigned = available[0]
    cursor.execute("INSERT OR REPLACE INTO users (user_id, chosen_name, assigned_name, attempts) VALUES (?, ?, ?, ?)",
                   (user_id, chosen_name, assigned, 1))
    conn.commit()
    return assigned

def get_user(user_id):
    cursor.execute("SELECT chosen_name, assigned_name, attempts FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def increment_attempt(user_id):
    cursor.execute("UPDATE users SET attempts = attempts + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

# ---- Bot Handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start", callback_data="start_process")]]
    await update.message.reply_text("Welcome ያህዌንሲ", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_start_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data = get_user(query.from_user.id)
    if user_data:
        await query.edit_message_text(
            f"👋 Welcome back {user_data[0]}!\nYou're already assigned: {user_data[1]}"
        )
        return

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"choose_{name}")]
        for name in user_names
    ]
    await query.edit_message_text(
        "Click your name from the following list:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_name_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chosen_name = query.data.replace("choose_", "")
    await query.answer()

    user_data = get_user(user_id)

    if user_data:
        _, assigned_name, attempts = user_data
        if attempts >= 2:
            await query.edit_message_text("❌ You've already tried twice. No more changes allowed.")
            return
        increment_attempt(user_id)
        await query.edit_message_text(
            f"😯 So you’re actually {chosen_name}?\nYou're still assigned to: *{assigned_name}*",
            parse_mode="Markdown"
        )
    else:
        assigned = assign_to_user(user_id, chosen_name)
        if not assigned:
            await query.edit_message_text("⚠️ Sorry, all names have been assigned.")
            return
        await query.edit_message_text(
            f"😯 Oooh you are {chosen_name}? How you doing?\n🎁 You got assigned to: *{assigned}*",
            parse_mode="Markdown"
        )

# ---- Main Bot Setup ----
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❗ Set the BOT_TOKEN environment variable.")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_start_process, pattern="start_process"))
    app.add_handler(CallbackQueryHandler(handle_name_choice, pattern="^choose_"))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
