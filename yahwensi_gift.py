from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
import os

# Assignments (Circular)
assignments = {
    "solomon": "selam",
    "selam": "yididya",
    "yididya": "eden",
    "eden": "bety tesfaye",
    "bety tesfaye": "bety melese",
    "bety melese": "bernabas",
    "bernabas": "mntie",
    "mntie": "frie",
    "frie": "aster ayana",
    "aster ayana": "aster bekalu",
    "aster bekalu": "sami",
    "sami": "feven",
    "feven": "bemni",
    "bemni": "elshu",
    "elshu": "solomon"
}

# Usernames Mapping (username → name)
usernames = {
    "Sol_african": "solomon",
    "Myfam1a4": "selam",
    "yidodi": "yididya",
    "bukne1": "eden",
    "rasnmegzat": "bety tesfaye",
    "Merertu19": "bety melese",
    "BarniYegeta": "bernabas",
    "GESDFL": "frie",
    "asterayana": "aster ayana",
    "asti4jc": "aster bekalu",
    "Grace1234589": "sami",
    "Fevi4christ": "feven",
    "BemnuD": "bemni",
    "ElshadayGech": "elshu"
}

# Special User with no username (mntie)
SPECIAL_USER_ID = 123456789  # Replace with actual user ID of "mntie"

ADMIN_USERNAME = "Sol_african"

# Database for logging views
conn = sqlite3.connect("views.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS views (
        username TEXT,
        name TEXT,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# Button list
name_list = list(assignments.keys())

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

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start", callback_data="start_process")]]
    await update.message.reply_text(
        "Welcome ያህዌንሲ!\n\n"
        "This bot helps you secretly assign someone to give a gift to.\n\n"
        "👉 How it works:\n"
        "- Click 'Start' to begin.\n"
        "- Choose your name from the list.\n"
        "- You'll be assigned a name (keep it secret 🤫).\n"
        "- You can only click your *own* name!\n\n"
        "⚠️ If you click another person's name, it won't work.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please select your name:", reply_markup=get_name_buttons())

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    user_id = query.from_user.id
    first_name = query.from_user.first_name
    chosen_name = query.data.replace("choose_", "")
    await query.answer()

    correct_name = usernames.get(username)

    # Handle mntie by user ID
    if user_id == SPECIAL_USER_ID:
        correct_name = "mntie"

    if correct_name != chosen_name:
      await query.edit_message_text(
        f"🚫 No, you are not {chosen_name}! Click your name below 👇:",
        reply_markup=get_name_buttons()
    )
    return


    # Log view
    cursor.execute(
        "INSERT INTO views (username, name) VALUES (?, ?)",
        (username or f"[NO_USERNAME] {first_name}", chosen_name)
    )
    conn.commit()

    assigned_name = assignments[chosen_name]
    await query.edit_message_text(
        f"🎁 You are assigned to: *{assigned_name}*\n🤫 Keep it secret!",
        parse_mode="Markdown"
    )

# Admin Commands
async def debug_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    msg = "📋 All Assignments:\n\n"
    for giver, receiver in assignments.items():
        msg += f"🎅 {giver} → 🎁 {receiver}\n"
    await update.message.reply_text(msg)

async def debug_views(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    cursor.execute("SELECT username, name, viewed_at FROM views ORDER BY viewed_at DESC")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("ℹ️ No one has viewed their assignment yet.")
        return
    msg = "👀 Views Log:\n\n"
    for username, name, viewed_at in rows:
        msg += f"📌 {username} viewed their assignment ({name}) at {viewed_at}\n"
    await update.message.reply_text(msg)

# Main Bot
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❗ Set BOT_TOKEN environment variable")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug_show", debug_show))
    app.add_handler(CommandHandler("debug_views", debug_views))
    app.add_handler(CallbackQueryHandler(start_process, pattern="start_process"))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern="^choose_"))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
