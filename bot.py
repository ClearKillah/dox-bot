import os
import json
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set
from flask import Flask, request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Import modules
from database import db
from groups import (
    create_group, join_group, leave_group,
    update_group_message, handle_group_message
)
from profile import (
    show_profile, edit_gender, set_gender,
    edit_age, set_age, edit_interests,
    toggle_interest, edit_avatar, set_avatar,
    show_stats
)
from help import show_help, show_help_menu, show_help_section

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = "8039344227:AAEDCP_902a3r52JIdM9REqUyPx-p2IVtxA"
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = "https://dox-bot-production.up.railway.app"
WELCOME_TEXT = """
👋 Добро пожаловать в анонимный чат!

🔍 Здесь вы можете:
• Найти случайного собеседника
• Создать или присоединиться к группе
• Настроить свой профиль
• Общаться анонимно

Используйте меню ниже для навигации.
"""

# Conversation states
START, CHATTING, PROFILE, EDIT_PROFILE, GROUP_CHATTING = range(5)

# Global variables
user_data: Dict[int, dict] = {}
active_chats: Dict[int, int] = {}
searching_users: Set[int] = set()
group_chats: Dict[str, dict] = {}
GROUP_MAX_MEMBERS = 10

# Keyboard layouts
MAIN_KEYBOARD = [
    [
        InlineKeyboardButton("🔍 Найти собеседника", callback_data="find_chat"),
        InlineKeyboardButton("👥 Группы", callback_data="groups")
    ],
    [
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("❓ Помощь", callback_data="help")
    ]
]

class ChatStats:
    def __init__(self):
        self.total_chats = 0
        self.active_chats = 0
        self.total_messages = 0
        self.total_users = 0

    def update(self):
        self.active_chats = len(active_chats) // 2
        self.total_users = len(user_data)

chat_stats = ChatStats()

# Create Flask app
app = Flask(__name__)

# Create Telegram application
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and send welcome message."""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            "gender": None,
            "age": None,
            "interests": [],
            "avatar": None,
            "stats": {"total_chats": 0, "messages_sent": 0}
        }
    
    welcome_message = await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Pin the welcome message
    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=welcome_message.message_id,
            disable_notification=True
        )
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
    
    return START

async def find_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start searching for a chat partner."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id in active_chats:
        await query.answer("Вы уже находитесь в чате!")
        return START
    
    searching_users.add(user_id)
    message = await query.edit_message_text(
        "🔍 Поиск собеседника...\nНажмите 'Пропустить' чтобы отменить поиск",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data="skip_search")]])
    )
    
    # Store message ID for later updates
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    context.user_data[f"last_message_{user_id}"] = message.message_id
    
    # Start continuous search
    asyncio.create_task(continuous_search(user_id, context))
    
    return START

async def continuous_search(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Continuously search for a chat partner."""
    while user_id in searching_users:
        for other_user in searching_users:
            if other_user != user_id:
                # Match found
                active_chats[user_id] = other_user
                active_chats[other_user] = user_id
                searching_users.remove(user_id)
                searching_users.remove(other_user)
                
                # Update both users' messages
                await update_chat_status(user_id, other_user, context)
                await update_chat_status(other_user, user_id, context)
                return
        
        await asyncio.sleep(1)
    
    # If user cancelled search
    if user_id in searching_users:
        searching_users.remove(user_id)
        try:
            await context.bot.edit_message_text(
                "Поиск отменен",
                chat_id=user_id,
                message_id=context.user_data.get(f"last_message_{user_id}")
            )
        except Exception as e:
            logger.error(f"Error updating message: {e}")

async def update_chat_status(user_id: int, partner_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Update chat status for both users."""
    message_text = "✅ Собеседник найден!\n\nИспользуйте /end чтобы завершить чат"
    keyboard = [[InlineKeyboardButton("❌ Завершить чат", callback_data="end_chat")]]
    
    try:
        await context.bot.edit_message_text(
            message_text,
            chat_id=user_id,
            message_id=context.user_data.get(f"last_message_{user_id}"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error updating chat status: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming messages."""
    user_id = update.effective_user.id
    
    if user_id not in active_chats:
        await update.message.reply_text(
            "Вы не находитесь в активном чате. Используйте /start для начала.",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
        return START
    
    partner_id = active_chats[user_id]
    
    # Forward message to partner
    try:
        if update.message.text:
            await context.bot.send_message(partner_id, update.message.text)
        elif update.message.photo:
            await context.bot.send_photo(partner_id, update.message.photo[-1].file_id)
        elif update.message.voice:
            await context.bot.send_voice(partner_id, update.message.voice.file_id)
        elif update.message.video:
            await context.bot.send_video(partner_id, update.message.video.file_id)
        elif update.message.sticker:
            await context.bot.send_sticker(partner_id, update.message.sticker.file_id)
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
    
    return CHATTING

async def skip_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip current search."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id in searching_users:
        searching_users.remove(user_id)
        await query.edit_message_text(
            "Поиск отменен",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
    
    return START

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the current chat."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        del active_chats[user_id]
        del active_chats[partner_id]
        
        # Update both users' messages
        await query.edit_message_text(
            "Чат завершен. Используйте /start для нового поиска.",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
        
        try:
            await context.bot.edit_message_text(
                "Собеседник покинул чат. Используйте /start для нового поиска.",
                chat_id=partner_id,
                message_id=context.user_data.get(f"last_message_{partner_id}"),
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
        except Exception as e:
            logger.error(f"Error updating partner message: {e}")
    
    return START

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callback queries."""
    query = update.callback_query
    data = query.data
    
    if data == "find_chat":
        return await find_chat(update, context)
    elif data == "skip_search":
        return await skip_search(update, context)
    elif data == "end_chat":
        return await end_chat(update, context)
    elif data == "back_to_main":
        await query.edit_message_text(
            WELCOME_TEXT,
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
            parse_mode=ParseMode.MARKDOWN
        )
        return START
    elif data == "help":
        await query.edit_message_text(
            "Справка:\n\n/start - Начать чат\n/help - Показать справку",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )
        return START
    elif data == "profile":
        await query.edit_message_text(
            "Ваш профиль:\n\nЭта функция будет доступна позже.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )
        return START
    elif data == "groups":
        await query.edit_message_text(
            "Групповые чаты:\n\nЭта функция будет доступна позже.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )
        return START
    
    return START

def setup_handlers():
    """Set up the handlers for the application."""
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [
                CallbackQueryHandler(handle_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
                MessageHandler(filters.PHOTO | filters.VOICE | filters.VIDEO | filters.STICKER, handle_message),
            ],
            CHATTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
                MessageHandler(filters.PHOTO | filters.VOICE | filters.VIDEO | filters.STICKER, handle_message),
                CallbackQueryHandler(handle_callback),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", lambda update, context: asyncio.run(handle_callback(update, context))))

async def setup_webhook():
    """Set up the webhook."""
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/telegram")
    logger.info(f"Webhook set up at {WEBHOOK_URL}/telegram")

@app.route('/', methods=['GET'])
def index():
    """Handle healthcheck requests."""
    return "Bot is running!"

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook requests."""
    if request.method == 'POST':
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            asyncio.run(application.process_update(update))
            return Response(status=200)
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return Response(status=500)
    return Response(status=200)

if __name__ == '__main__':
    # Set up handlers
    setup_handlers()
    
    # Set up webhook
    asyncio.run(setup_webhook())
    
    # Run Flask application
    app.run(host='0.0.0.0', port=PORT) 