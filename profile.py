import os
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db

# Profile states
PROFILE_MAIN, PROFILE_GENDER, PROFILE_AGE, PROFILE_INTERESTS, PROFILE_AVATAR = range(5)

# Interest options
INTERESTS = ["💝 Флирт", "💬 Общение", "🎮 Игры", "🎵 Музыка", "📚 Книги", "🎬 Фильмы"]

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user profile menu."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    message_text = f"""
👤 Ваш профиль:

{'👨' if user_data.get('gender') == 'male' else '👩' if user_data.get('gender') else '❓'} Пол: {user_data.get('gender', 'Не указан')}
🎂 Возраст: {user_data.get('age', 'Не указан')}
💫 Интересы: {', '.join(user_data.get('interests', [])) or 'Не указаны'}
"""
    
    keyboard = [
        [InlineKeyboardButton("👤 Изменить пол", callback_data="edit_gender")],
        [InlineKeyboardButton("🎂 Изменить возраст", callback_data="edit_age")],
        [InlineKeyboardButton("💫 Изменить интересы", callback_data="edit_interests")],
        [InlineKeyboardButton("🖼 Изменить аватар", callback_data="edit_avatar")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PROFILE_MAIN

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start gender editing process."""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("👨 Мужской", callback_data="set_gender_male")],
        [InlineKeyboardButton("👩 Женский", callback_data="set_gender_female")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
    ]
    
    await query.edit_message_text(
        "Выберите ваш пол:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PROFILE_GENDER

async def set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set user gender."""
    query = update.callback_query
    user_id = query.from_user.id
    gender = query.data.split('_')[2]
    
    user_data = db.get_user(user_id)
    user_data['gender'] = gender
    db.save_user(user_id, user_data)
    
    await query.answer("Пол успешно обновлен!")
    return await show_profile(update, context)

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start age editing process."""
    query = update.callback_query
    
    await query.edit_message_text(
        "Введите ваш возраст (от 18 до 100):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]])
    )
    
    return PROFILE_AGE

async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set user age."""
    user_id = update.effective_user.id
    try:
        age = int(update.message.text)
        if not (18 <= age <= 100):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректный возраст (от 18 до 100):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]])
        )
        return PROFILE_AGE
    
    user_data = db.get_user(user_id)
    user_data['age'] = age
    db.save_user(user_id, user_data)
    
    await update.message.reply_text("Возраст успешно обновлен!")
    return await show_profile(update, context)

async def edit_interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start interests editing process."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    current_interests = set(user_data.get('interests', []))
    
    keyboard = []
    for interest in INTERESTS:
        status = "✅" if interest in current_interests else "⬜️"
        keyboard.append([InlineKeyboardButton(f"{status} {interest}", callback_data=f"toggle_interest_{interest}")])
    keyboard.append([InlineKeyboardButton("💾 Сохранить", callback_data="save_interests")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    await query.edit_message_text(
        "Выберите ваши интересы:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PROFILE_INTERESTS

async def toggle_interest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle interest selection."""
    query = update.callback_query
    user_id = query.from_user.id
    interest = query.data.split('_')[2]
    
    user_data = db.get_user(user_id)
    interests = set(user_data.get('interests', []))
    
    if interest in interests:
        interests.remove(interest)
    else:
        interests.add(interest)
    
    user_data['interests'] = list(interests)
    db.save_user(user_id, user_data)
    
    return await edit_interests(update, context)

async def edit_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start avatar editing process."""
    query = update.callback_query
    
    await query.edit_message_text(
        "Отправьте новое фото для аватара:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]])
    )
    
    return PROFILE_AVATAR

async def set_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set user avatar."""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text(
            "Пожалуйста, отправьте фото:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]])
        )
        return PROFILE_AVATAR
    
    # Create avatars directory if it doesn't exist
    os.makedirs("avatars", exist_ok=True)
    
    # Get the largest photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    
    # Save avatar
    avatar_path = f"avatars/{user_id}.jpg"
    await file.download_to_drive(avatar_path)
    
    user_data = db.get_user(user_id)
    user_data['avatar'] = avatar_path
    db.save_user(user_id, user_data)
    
    await update.message.reply_text("Аватар успешно обновлен!")
    return await show_profile(update, context)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user statistics."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    stats = user_data.get('stats', {})
    
    message_text = f"""
📊 Ваша статистика:

💬 Всего чатов: {stats.get('total_chats', 0)}
📝 Отправлено сообщений: {stats.get('messages_sent', 0)}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]]
    
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PROFILE_MAIN 