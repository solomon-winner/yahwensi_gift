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

# Admin username
ADMIN_USERNAME = "Sol_african"

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

def reset_user(user_id):
    cursor.execute("SELECT assigned_name FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        assigned_name = result[0]
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM assigned_names WHERE name = ?", (assigned_name,))
        conn.commit()
        return True
    return False

def show_all_assignments():
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

def clear_all():
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM assigned_names")
    conn.commit()

def delete_by_name(name):
    cursor.execute("SELECT user_id FROM users WHERE chosen_name = ?", (name,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        return reset_user(user_id)
    return False

def get_name_buttons():
    keyboard = []
    row = []
    for idx, name in enumerate(name_list):
        row.append(InlineKeyboardButton(name, callback_data=f"choose_{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start", callback_data="start_process")]]
    await update.message.reply_text(
        "Welcome ያህዌንሲ!\n\nThis bot will help you secretly assign someone to give a gift to.\nClick start and pick your name. You'll then be shown *only one* name to give your gift to — and only you will know. 🤫\n\nYou can retry once if you mistakenly select the wrong name.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_data = get_user(user_id)
    if user_data and user_data[2] is not None and user_data[1] is not None and user_data[2] != "":
        if user_data[2] != "" and user_data[1] != "":
            await query.edit_message_text(
                f"👋 Welcome back {user_data[0]}!\nYou're assigned to: *{user_data[1]}*\n(Shhh, keep it secret!)",
                parse_mode="Markdown"
            )
            return

    await query.edit_message_text("Click your name from the list:", reply_markup=get_name_buttons())

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
        await query.edit_message_text("Click your name from the list:", reply_markup=get_name_buttons())
    else:
        assigned = assign_name(user_id, chosen_name)
        if not assigned:
            await query.edit_message_text("⚠️ Sorry, all names have been assigned or only your own name is left.")
            return
        retry_keyboard = [[InlineKeyboardButton("😅 Sorry, I clicked the wrong name (retry)", callback_data="retry")]]
        await query.edit_message_text(
            f"🎉 Oooh you are *{chosen_name}*? How you doing?\n🎁 You are giving your gift to: *{assigned}*\n🤫 (Shhh... Keep it secret!)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(retry_keyboard)
        )

async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_data = get_user(user_id)
    if user_data:
        _, _, attempts = user_data
        if attempts >= 2:
            await query.edit_message_text("❌ You already retried once. You cannot retry again.")
            return
        increment_attempt(user_id)
        await query.edit_message_text("Click your name from the list:", reply_markup=get_name_buttons())

# Admin-only: View DB and clear
async def debug_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        print("❗ Unauthorized access attempt by:", update.effective_user.username)
        return
    data = show_all_assignments()
    if not data:
        await update.message.reply_text("📦 No assignments yet.")
        return
    msg = "📋 All Assignments:\n\n"
    for user_id, name, assigned, attempts in data:
        msg += f"👤 {name} → 🎁 {assigned} (tries: {attempts})\n"
    await update.message.reply_text(msg)

async def debug_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    clear_all()
    await update.message.reply_text("🗑 All assignments cleared.")

async def debug_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    args = context.args
    if not args:
        await update.message.reply_text("❗ Please provide a name to delete. Usage: /debug_delete <name>")
        return
    name = " ".join(args).strip().lower()
    success = delete_by_name(name)
    if success:
        await update.message.reply_text(f"✅ Deleted assignment for: {name}")
    else:
        await update.message.reply_text(f"❌ No assignment found for: {name}")

# Run Bot
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❗ Set BOT_TOKEN environment variable")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug_show", debug_show))
    app.add_handler(CommandHandler("debug_clear", debug_clear))
    app.add_handler(CommandHandler("debug_delete", debug_delete))
    app.add_handler(CallbackQueryHandler(start_process, pattern="start_process"))
    app.add_handler(CallbackQueryHandler(handle_retry, pattern="retry"))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern="^choose_"))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
