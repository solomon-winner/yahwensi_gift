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

def get_all_users():
    cursor.execute("SELECT user_id, chosen_name FROM users")
    return cursor.fetchall()

def assign_name(user_id, chosen_name):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, chosen_name) VALUES (?, ?)", (user_id, chosen_name))
    conn.commit()


def finalize_assignments():
    users = get_all_users()
    if len(users) < 2:
        return False, "🚫 Not enough participants to finalize."

    random.shuffle(users)
    for i in range(len(users)):
        giver_id, giver_name = users[i]
        _, receiver_name = users[(i + 1) % len(users)]
        cursor.execute("UPDATE users SET assigned_name = ? WHERE user_id = ?", (receiver_name, giver_id))
        cursor.execute("INSERT OR IGNORE INTO assigned_names (name) VALUES (?)", (receiver_name,))
    conn.commit()
    return True, "✅ Final assignments completed."

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
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM assigned_names WHERE name = ?", (name,))
        conn.commit()
        return True
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
        "Welcome ያህዌንሲ!\n\nThis bot will help you secretly assign someone to give a gift to.\nClick start and pick your name. After the admin finalizes, you'll see who you give a gift to. 🤫\n\nYou can retry once if you mistakenly select the wrong name.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_data = get_user(user_id)
    if user_data and user_data[1]:
        if user_data[2]:
            await query.edit_message_text(
                f"🎁 You are giving your gift to: *{user_data[2]}*\n🤫 (Shhh... keep it secret!)",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("Click your name from the list:", reply_markup=get_name_buttons())
    else:
        await query.edit_message_text("Click your name from the list:", reply_markup=get_name_buttons())

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chosen_name = query.data.replace("choose_", "")
    await query.answer()

    assign_name(user_id, chosen_name)
    retry_keyboard = [[InlineKeyboardButton("😅 Sorry, I clicked the wrong name (retry)", callback_data="retry")]]
    await query.edit_message_text(
        f"🎉 Hello *{chosen_name}*!\n✅ Your choice is saved.\nWait for the admin to finalize assignments.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(retry_keyboard)
    )

async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    await query.edit_message_text("Click your name from the list:", reply_markup=get_name_buttons())

# Admin-only: View DB and clear
async def debug_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    data = show_all_assignments()
    if not data:
        await update.message.reply_text("📦 No assignments yet.")
        return
    msg = "📋 All Assignments:\n\n"
    for user_id, name, assigned, attempts in data:
        msg += f"👤 {name} → 🎁 {assigned if assigned else 'Not assigned'} (tries: {attempts})\n"
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

async def debug_finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    success, message = finalize_assignments()
    await update.message.reply_text(message)

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
    app.add_handler(CommandHandler("debug_finalize", debug_finalize))
    app.add_handler(CallbackQueryHandler(start_process, pattern="start_process"))
    app.add_handler(CallbackQueryHandler(handle_retry, pattern="retry"))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern="^choose_"))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
