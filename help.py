from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

HELP_TEXT = """
🤖 *Анонимный Чат-бот*

*Основные команды:*
/start - Начать работу с ботом
/help - Показать это сообщение
/end - Завершить текущий чат
/profile - Открыть профиль
/groups - Управление группами

*Приватные чаты:*
• Нажмите "🔍 Найти собеседника" для начала поиска
• Отправляйте любые сообщения (текст, фото, голосовые, видео, стикеры)
• Используйте кнопку "Пропустить" для поиска нового собеседника
• Нажмите "Завершить чат" для окончания разговора

*Групповые чаты:*
• Создайте группу и получите код приглашения
• Поделитесь кодом с друзьями
• Максимум 10 участников в группе
• Все сообщения анонимны

*Профиль:*
• Укажите пол и возраст
• Загрузите аватар
• Выберите интересы
• Просматривайте статистику

*Безопасность:*
• Все сообщения анонимны
• История чатов автоматически удаляется
• Личная информация защищена
• Группы имеют ограничение на участников

*Правила использования:*
1. Уважайте других пользователей
2. Не отправляйте спам
3. Не нарушайте правила Telegram
4. Сообщайте о нарушениях администраторам

*Поддержка:*
Если у вас возникли проблемы или вопросы, обратитесь к администраторам.
"""

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message."""
    query = update.callback_query if update.callback_query else None
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    if query:
        await query.edit_message_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help menu with different sections."""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("💬 Приватные чаты", callback_data="help_private")],
        [InlineKeyboardButton("👥 Групповые чаты", callback_data="help_groups")],
        [InlineKeyboardButton("👤 Профиль", callback_data="help_profile")],
        [InlineKeyboardButton("🔒 Безопасность", callback_data="help_security")],
        [InlineKeyboardButton("📜 Правила", callback_data="help_rules")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        "Выберите раздел справки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_help_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show specific help section."""
    query = update.callback_query
    section = query.data.split('_')[1]
    
    sections = {
        "private": """
*💬 Приватные чаты*

• Нажмите "🔍 Найти собеседника" для начала поиска
• Отправляйте любые сообщения (текст, фото, голосовые, видео, стикеры)
• Используйте кнопку "Пропустить" для поиска нового собеседника
• Нажмите "Завершить чат" для окончания разговора
• Все сообщения анонимны
• История чатов автоматически удаляется
""",
        "groups": """
*👥 Групповые чаты*

• Создайте группу и получите код приглашения
• Поделитесь кодом с друзьями
• Максимум 10 участников в группе
• Все сообщения анонимны
• Управление участниками
• Автоматическое удаление пустых групп
""",
        "profile": """
*👤 Профиль*

• Укажите пол и возраст
• Загрузите аватар (виден только вам)
• Выберите интересы
• Просматривайте статистику чатов
• Все данные сохраняются анонимно
""",
        "security": """
*🔒 Безопасность*

• Все сообщения передаются анонимно
• История чатов автоматически удаляется
• Личная информация защищена
• Группы имеют ограничение на участников
• Сообщения не сохраняются на сервере
""",
        "rules": """
*📜 Правила использования*

1. Уважайте других пользователей
2. Не отправляйте спам
3. Не нарушайте правила Telegram
4. Сообщайте о нарушениях администраторам
5. Не раскрывайте личную информацию
6. Не используйте бота для рекламы
"""
    }
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="help_menu")]]
    
    await query.edit_message_text(
        sections.get(section, "Раздел не найден"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    ) 