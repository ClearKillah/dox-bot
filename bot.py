import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
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
from aiohttp import web

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
    await context.bot.pin_chat_message(
        chat_id=update.effective_chat.id,
        message_id=welcome_message.message_id,
        disable_notification=True
    )
    
    return START

async def find_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start searching for a chat partner."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id in active_chats:
        await query.answer("Вы уже находитесь в чате!")
        return START
    
    searching_users.add(user_id)
    await query.edit_message_text(
        "🔍 Поиск собеседника...\nНажмите 'Пропустить' чтобы отменить поиск",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data="skip_search")]])
    )
    
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
                
                # Update statistics
                db.update_user_stats(user_id, chat_count=1)
                db.update_user_stats(other_user, chat_count=1)
                return
        
        await asyncio.sleep(1)
    
    # If user cancelled search
    if user_id in searching_users:
        searching_users.remove(user_id)
        await context.bot.edit_message_text(
            "Поиск отменен",
            chat_id=user_id,
            message_id=context.user_data.get("last_message_id")
        )

async def update_chat_status(user_id: int, partner_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Update chat status for both users."""
    message_text = "✅ Собеседник найден!\n\nИспользуйте /end чтобы завершить чат"
    keyboard = [[InlineKeyboardButton("❌ Завершить чат", callback_data="end_chat")]]
    
    await context.bot.edit_message_text(
        message_text,
        chat_id=user_id,
        message_id=context.user_data.get("last_message_id"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
    
    # Update message count
    db.update_user_stats(user_id, message_count=1)
    
    return CHATTING

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
        
        await context.bot.edit_message_text(
            "Собеседник покинул чат. Используйте /start для нового поиска.",
            chat_id=partner_id,
            message_id=context.user_data.get("last_message_id"),
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
    
    return START

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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callback queries."""
    query = update.callback_query
    data = query.data
    
    if data == "back_to_main":
        await query.edit_message_text(
            WELCOME_TEXT,
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
            parse_mode=ParseMode.MARKDOWN
        )
        return START
    
    elif data == "help":
        return await show_help(update, context)
    
    elif data == "help_menu":
        return await show_help_menu(update, context)
    
    elif data.startswith("help_"):
        return await show_help_section(update, context)
    
    elif data == "profile":
        return await show_profile(update, context)
    
    elif data == "edit_gender":
        return await edit_gender(update, context)
    
    elif data.startswith("set_gender_"):
        return await set_gender(update, context)
    
    elif data == "edit_age":
        return await edit_age(update, context)
    
    elif data == "edit_interests":
        return await edit_interests(update, context)
    
    elif data.startswith("toggle_interest_"):
        return await toggle_interest(update, context)
    
    elif data == "edit_avatar":
        return await edit_avatar(update, context)
    
    elif data == "show_stats":
        return await show_stats(update, context)
    
    elif data == "groups":
        keyboard = [
            [InlineKeyboardButton("➕ Создать группу", callback_data="create_group")],
            [InlineKeyboardButton("🔍 Найти группу", callback_data="find_group")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        await query.edit_message_text(
            "👥 Управление группами\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return START
    
    elif data == "create_group":
        return await create_group(update, context)
    
    elif data.startswith("join_group_"):
        return await join_group(update, context)
    
    elif data.startswith("leave_group_"):
        return await leave_group(update, context)
    
    elif data.startswith("manage_group_"):
        group_code = data.split('_')[2]
        group_data = db.get_group(group_code)
        if group_data and query.from_user.id == group_data["creator_id"]:
            keyboard = [
                [InlineKeyboardButton("❌ Удалить группу", callback_data=f"delete_group_{group_code}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            await query.edit_message_text(
                f"Управление группой {group_code}\n\nВыберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return START
    
    elif data.startswith("delete_group_"):
        group_code = data.split('_')[2]
        group_data = db.get_group(group_code)
        if group_data and query.from_user.id == group_data["creator_id"]:
            db.delete_group(group_code)
            await query.edit_message_text(
                "Группа успешно удалена",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
        return START
    
    return START

async def healthcheck(request):
    """Handle healthcheck requests."""
    return web.Response(text="OK", status=200)

async def webhook_handler(request):
    """Handle incoming webhook requests."""
    if request.method == "POST":
        try:
            data = await request.json()
            update = Update.de_json(data, bot)
            await application.process_update(update)
            return web.Response(status=200)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return web.Response(status=500)
    return web.Response(status=200)

async def on_startup(app):
    """Set up webhook on startup."""
    try:
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info("Webhook set successfully")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

async def on_shutdown(app):
    """Remove webhook on shutdown."""
    try:
        await bot.delete_webhook()
        logger.info("Webhook removed successfully")
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")

def setup_app():
    """Set up the application."""
    global bot, application
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()
    bot = application.bot

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
            PROFILE: [
                CallbackQueryHandler(handle_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_age),
                MessageHandler(filters.PHOTO, set_avatar),
            ],
            EDIT_PROFILE: [
                CallbackQueryHandler(handle_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_age),
                MessageHandler(filters.PHOTO, set_avatar),
            ],
            GROUP_CHATTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message),
                MessageHandler(filters.PHOTO | filters.VOICE | filters.VIDEO | filters.STICKER, handle_group_message),
                CallbackQueryHandler(handle_callback),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", show_help))

    # Create web application
    app = web.Application()
    
    # Add routes
    app.router.add_get("/", healthcheck)
    app.router.add_post("/", webhook_handler)
    
    # Add startup and shutdown handlers
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app

# Create the application instance
app = setup_app()

if __name__ == '__main__':
    # This is for local development
    web.run_app(app, host='0.0.0.0', port=PORT) 