import random
import string
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db

def generate_group_code() -> str:
    """Generate a random 6-character group code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def create_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a new group chat."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Generate unique group code
    group_code = generate_group_code()
    while group_code in db.group_data:
        group_code = generate_group_code()
    
    # Create group data
    group_data = {
        "creator_id": user_id,
        "members": [user_id],
        "created_at": str(datetime.now()),
        "code": group_code
    }
    
    db.save_group(group_code, group_data)
    
    # Send success message with group code
    message_text = f"""
✅ Группа создана!

🔑 Код группы: {group_code}
👥 Участников: 1/{GROUP_MAX_MEMBERS}

Поделитесь кодом с друзьями, чтобы они могли присоединиться.
"""
    
    keyboard = [
        [InlineKeyboardButton("👥 Управление группой", callback_data=f"manage_group_{group_code}")],
        [InlineKeyboardButton("❌ Удалить группу", callback_data=f"delete_group_{group_code}")]
    ]
    
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def join_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Join a group using its code."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get group code from callback data
    group_code = query.data.split('_')[2]
    group_data = db.get_group(group_code)
    
    if not group_data:
        await query.answer("Группа не найдена!")
        return
    
    if user_id in group_data["members"]:
        await query.answer("Вы уже являетесь участником этой группы!")
        return
    
    if len(group_data["members"]) >= GROUP_MAX_MEMBERS:
        await query.answer("Группа уже заполнена!")
        return
    
    # Add user to group
    group_data["members"].append(user_id)
    db.save_group(group_code, group_data)
    
    # Update group message
    await update_group_message(group_code, context)
    
    await query.answer("Вы успешно присоединились к группе!")

async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Leave a group."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get group code from callback data
    group_code = query.data.split('_')[2]
    group_data = db.get_group(group_code)
    
    if not group_data or user_id not in group_data["members"]:
        await query.answer("Ошибка: группа не найдена!")
        return
    
    # Remove user from group
    group_data["members"].remove(user_id)
    
    if not group_data["members"]:
        # Delete empty group
        db.delete_group(group_code)
        await query.edit_message_text("Группа удалена, так как все участники покинули её.")
    else:
        # Update group data and message
        db.save_group(group_code, group_data)
        await update_group_message(group_code, context)
        await query.answer("Вы покинули группу!")

async def update_group_message(group_code: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the group information message."""
    group_data = db.get_group(group_code)
    if not group_data:
        return
    
    message_text = f"""
👥 Группа {group_code}

👤 Участники ({len(group_data['members'])}/{GROUP_MAX_MEMBERS}):
"""
    
    for i, member_id in enumerate(group_data["members"], 1):
        user_data = db.get_user(member_id)
        gender = "👨" if user_data.get("gender") == "male" else "👩"
        message_text += f"{i}. {gender} Участник {i}\n"
    
    keyboard = []
    if len(group_data["members"]) < GROUP_MAX_MEMBERS:
        keyboard.append([InlineKeyboardButton("➕ Присоединиться", callback_data=f"join_group_{group_code}")])
    keyboard.append([InlineKeyboardButton("❌ Покинуть группу", callback_data=f"leave_group_{group_code}")])
    
    # Update message for all group members
    for member_id in group_data["members"]:
        try:
            await context.bot.edit_message_text(
                message_text,
                chat_id=member_id,
                message_id=context.user_data.get(f"group_message_{group_code}_{member_id}"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Error updating message for user {member_id}: {e}")

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages in group chats."""
    user_id = update.effective_user.id
    message = update.message
    
    # Find which group the user is in
    for group_code, group_data in db.group_data.items():
        if user_id in group_data["members"]:
            # Forward message to all other group members
            for member_id in group_data["members"]:
                if member_id != user_id:
                    try:
                        if message.text:
                            await context.bot.send_message(member_id, message.text)
                        elif message.photo:
                            await context.bot.send_photo(member_id, message.photo[-1].file_id)
                        elif message.voice:
                            await context.bot.send_voice(member_id, message.voice.file_id)
                        elif message.video:
                            await context.bot.send_video(member_id, message.video.file_id)
                        elif message.sticker:
                            await context.bot.send_sticker(member_id, message.sticker.file_id)
                    except Exception as e:
                        print(f"Error forwarding message to user {member_id}: {e}")
            break 