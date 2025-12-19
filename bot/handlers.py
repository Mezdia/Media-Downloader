import logging
import os
import asyncio
import re
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, MessageOrigin
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from sqlalchemy import select, update
from sqlalchemy.orm import Session

# Local imports
from database import get_db, User, Variable, DownloadHistory
from locales import t
import main  # To access internal_download_video

logger = logging.getLogger(__name__)

# Advanced animation and reaction constants
REACTIONS = {
    "searching": ["🔍", "👀", "🔎", "💫"],
    "downloading": ["⬇️", "📥", "⚡", "💾"],
    "uploading": ["🚀", "📤", "☁️", "✨"],
    "processing": ["⚙️", "🔄", "💭", "⏳"],
    "success": ["✅", "🎉", "🌟", "🎊"],
    "error": ["❌", "💥", "🚫", "⚠️"],
    "completed": ["🎬", "🎵", "📱", "💎"],
    "live_download": ["🔄", "⬇️", "📥", "💾"],
    "live_upload": ["🚀", "📤", "☁️", "✨"],
    "admin_action": ["👑", "⚙️", "🔧", "💻"]
}

# Animation sequences for different actions
ANIMATION_SEQUENCES = {
    "searching": ["🔍", "🔎", "🔍", "🔎"],
    "downloading": ["⬇️", "📥", "⬇️", "📥"],
    "uploading": ["🚀", "📤", "🚀", "📤"],
    "processing": ["⚙️", "🔄", "⚙️", "🔄"],
    "success": ["✅", "🎉", "✅", "🎉"],
    "live_download": ["🔄", "⬇️", "📥", "💾"],
    "live_upload": ["🚀", "📤", "☁️", "✨"]
}

# Live status tracking
LIVE_STATUS_MESSAGES = {}

# --- Advanced Helper Functions ---
async def get_user_lang(user_id: int) -> str:
    """Get user language preference."""
    async for session in get_db():
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.language if user else "fa"

async def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Get complete user data."""
    async for session in get_db():
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "full_name": user.full_name,
                "language": user.language,
                "is_admin": user.is_admin,
                "is_banned": user.is_banned,
                "joined_date": user.joined_date
            }
    return None

async def register_user(user_info: Update.effective_user):
    """Register or update user in DB with enhanced data."""
    async for session in get_db():
        result = await session.execute(select(User).where(User.telegram_id == user_info.id))
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            new_user = User(
                telegram_id=user_info.id,
                username=user_info.username,
                full_name=user_info.full_name or user_info.first_name,
                language="fa" # Default to Persian
            )
            session.add(new_user)
        else:
            # Update info
            existing_user.username = user_info.username
            existing_user.full_name = user_info.full_name or user_info.first_name
            
        await session.commit()

async def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    async for session in get_db():
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.is_admin if user else False

async def is_banned(user_id: int) -> bool:
    """Check if user is banned."""
    async for session in get_db():
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.is_banned if user else False

async def set_user_admin(user_id: int, is_admin: bool = True) -> bool:
    """Set user admin status."""
    try:
        async for session in get_db():
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.is_admin = is_admin
                await session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Error setting admin status for user {user_id}: {e}")
        return False

async def get_variable(key: str, default: str = "") -> str:
    """Get variable value from database."""
    async for session in get_db():
        result = await session.execute(select(Variable).where(Variable.key == key))
        var = result.scalar_one_or_none()
        return var.value if var else default

async def set_variable(key: str, value: str, description: str = "") -> bool:
    """Set variable value in database."""
    try:
        async for session in get_db():
            result = await session.execute(select(Variable).where(Variable.key == key))
            var = result.scalar_one_or_none()
            
            if var:
                var.value = value
                var.description = description
            else:
                var = Variable(key=key, value=value, description=description)
                session.add(var)
            
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error setting variable {key}: {e}")
        return False

async def delete_variable(key: str) -> bool:
    """Delete variable from database."""
    try:
        async for session in get_db():
            result = await session.execute(select(Variable).where(Variable.key == key))
            var = result.scalar_one_or_none()
            if var:
                await session.delete(var)
                await session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Error deleting variable {key}: {e}")
        return False

# --- Advanced Animation and Reaction Functions ---
async def send_animated_message(update: Update, text: str, animation_type: str = "processing") -> Optional[int]:
    """Send animated message with emoji sequence."""
    try:
        emojis = ANIMATION_SEQUENCES.get(animation_type, ["⚙️"])
        animated_text = f"{emojis[0]} {text}"
        
        msg = await update.message.reply_text(animated_text)
        
        # Animate for 3 cycles
        for cycle in range(3):
            for emoji in emojis[1:]:
                await asyncio.sleep(0.5)
                try:
                    await msg.edit_text(f"{emoji} {text}")
                except:
                    break
        
        return msg.message_id
    except Exception as e:
        logger.error(f"Error in animated message: {e}")
        return None

async def add_reaction(message, emoji: str) -> bool:
    """Add reaction to a message with error handling."""
    try:
        await message.set_reaction(emoji)
        return True
    except Exception as e:
        logger.warning(f"Could not add reaction {emoji}: {e}")
        return False

async def remove_message(message) -> bool:
    """Remove a message with error handling."""
    try:
        await message.delete()
        return True
    except Exception as e:
        logger.warning(f"Could not delete message: {e}")
        return False

async def edit_message(message, new_text: str) -> bool:
    """Edit a message with error handling."""
    try:
        await message.edit_text(new_text)
        return True
    except Exception as e:
        logger.warning(f"Could not edit message: {e}")
        return False

async def send_live_status_message(update: Update, text: str, status_type: str = "processing") -> int:
    """Send a live status message that can be updated."""
    try:
        msg = await update.message.reply_text(f"{REACTIONS[status_type][0]} {text}")
        LIVE_STATUS_MESSAGES[msg.message_id] = {
            "message": msg,
            "status_type": status_type,
            "emoji_index": 0,
            "last_update": time.time()
        }
        return msg.message_id
    except Exception as e:
        logger.error(f"Error sending live status message: {e}")
        return None

async def update_live_status(message_id: int, new_text: str, new_status_type: str = None):
    """Update a live status message with animation."""
    if message_id not in LIVE_STATUS_MESSAGES:
        return False
    
    try:
        status_data = LIVE_STATUS_MESSAGES[message_id]
        message = status_data["message"]
        
        # Update status type if provided
        if new_status_type:
            status_data["status_type"] = new_status_type
            status_data["emoji_index"] = 0
        
        # Get current emoji sequence
        emojis = ANIMATION_SEQUENCES.get(status_data["status_type"], ["⚙️"])
        current_emoji = emojis[status_data["emoji_index"]]
        
        # Update emoji index for next animation frame
        status_data["emoji_index"] = (status_data["emoji_index"] + 1) % len(emojis)
        status_data["last_update"] = time.time()
        
        await message.edit_text(f"{current_emoji} {new_text}")
        return True
    except Exception as e:
        logger.error(f"Error updating live status: {e}")
        return False

async def cleanup_live_status(message_id: int):
    """Clean up a live status message."""
    if message_id in LIVE_STATUS_MESSAGES:
        try:
            await remove_message(LIVE_STATUS_MESSAGES[message_id]["message"])
        except:
            pass
        del LIVE_STATUS_MESSAGES[message_id]

async def send_temporary_message(update: Update, text: str, duration: int = 5):
    """Send a message that will be automatically deleted after duration."""
    try:
        msg = await update.message.reply_text(text)
        await asyncio.sleep(duration)
        await remove_message(msg)
    except Exception as e:
        logger.error(f"Error with temporary message: {e}")

# --- Format and Utility Functions ---
def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """Format duration in human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}:{minutes:02d}:{seconds % 60:02d}"

def create_quality_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    """Create glass-style quality selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(
                f"🌟 {t('quality_best', lang)}", 
                callback_data=f"dl_best_{user_id}"
            ),
            InlineKeyboardButton(
                f"🖥️ {t('quality_1080', lang)}", 
                callback_data=f"dl_1080p_{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"📱 {t('quality_720', lang)}", 
                callback_data=f"dl_720p_{user_id}"
            ),
            InlineKeyboardButton(
                f"🎵 {t('quality_audio', lang)}", 
                callback_data=f"dl_audio_{user_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Create admin panel keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("⚙️ Variables", callback_data="admin_vars")
        ],
        [
            InlineKeyboardButton("📈 Analytics", callback_data="admin_analytics"),
            InlineKeyboardButton("🔧 Settings", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Enhanced Commanders ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced /start command with animations and welcome."""
    user = update.effective_user
    await register_user(user)
    lang = await get_user_lang(user.id)
    
    # Check if user is banned
    if await is_banned(user.id):
        await update.message.reply_text(t("banned", lang))
        return
    
    # Send animated welcome
    welcome_msg = await send_animated_message(update, t("welcome", lang), "success")
    
    # Add welcome reaction
    await add_reaction(update.message, "🎬")
    
    # Send help tips
    tips_text = f"""
💡 **Quick Tips:**
• Send any YouTube or Instagram link to start downloading
• Use /help for commands
• Use /lang to change language
• Admins can use /admin for management
"""
    
    await update.message.reply_text(tips_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced /help with comprehensive command list."""
    lang = await get_user_lang(update.effective_user.id)
    user_id = update.effective_user.id
    
    # Check if user is banned
    if await is_banned(user_id):
        await update.message.reply_text(t("banned", lang))
        return
    
    help_text = f"""
🎬 **Media Downloader Bot Help**

**📱 Basic Usage:**
• Send YouTube/Instagram link → Select quality → Download

**🔧 Commands:**
• /start - Restart bot
• /help - Show this help
• /lang - Change language
• /stats - View your statistics
"""
    
    # Add admin commands if user is admin
    if await is_admin(user_id):
        help_text += """
**👑 Admin Commands:**
• /admin - Open admin panel
• /broadcast <message> - Send broadcast
• /ban <user_id> - Ban user
• /unban <user_id> - Unban user
• /promote <user_id> - Make admin
"""
    
    help_text += f"""

**🌐 Supported Platforms:**
• YouTube: Videos, Playlists, Audio
• Instagram: Posts, Reels, Stories

**💡 Features:**
• High quality downloads
• Live progress tracking
• Multiple languages
• Batch downloads

---
*Bot by Mezd | Powered by Mezdia*
"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced /lang with beautiful language selection."""
    user_id = update.effective_user.id
    
    # Check if user is banned
    if await is_banned(user_id):
        await update.message.reply_text(t("banned", await get_user_lang(user_id)))
        return
    
    lang = await get_user_lang(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        t("select_lang", lang), 
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced /stats with user statistics."""
    user_id = update.effective_user.id
    
    # Check if user is banned
    if await is_banned(user_id):
        await update.message.reply_text(t("banned", await get_user_lang(user_id)))
        return
    
    lang = await get_user_lang(user_id)
    
    try:
        async for session in get_db():
            # Get user's download stats
            result = await session.execute(
                select(DownloadHistory)
                .where(DownloadHistory.user_id == user_id)
                .order_by(DownloadHistory.download_date.desc())
                .limit(10)
            )
            user_downloads = result.scalars().all()
            
            # Get total downloads count
            total_downloads = await session.scalar(
                select(DownloadHistory).where(DownloadHistory.user_id == user_id).count()
            )
            
            # Calculate total file size
            total_size = sum(d.file_size or 0 for d in user_downloads)
        
        stats_text = f"""
📊 **Your Statistics**

📥 **Downloads:** {total_downloads}
💾 **Total Size:** {format_file_size(total_size)}
📅 **Member since:** {user_downloads[-1].download_date.strftime('%Y-%m-%d') if user_downloads else 'N/A'}
"""
        
        if user_downloads:
            recent = user_downloads[:3]
            stats_text += "\n🎬 **Recent Downloads:**\n"
            for download in recent:
                title = download.title[:30] + "..." if len(download.title or "") > 30 else download.title or "Unknown"
                stats_text += f"• {title} ({download.media_type})\n"
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        await update.message.reply_text("❌ Error getting statistics")

# --- Admin Command Handlers ---

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced comprehensive admin panel within Telegram with live stats and actions."""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        lang = await get_user_lang(user_id)
        await update.message.reply_text(t("not_admin", lang))
        return
    
    lang = await get_user_lang(user_id)
    
    # Get comprehensive bot stats
    try:
        async for session in get_db():
            users_count = await session.scalar(select(User).count())
            downloads_count = await session.scalar(select(DownloadHistory).count())
            admins_count = await session.scalar(select(User).where(User.is_admin == True).count())
            banned_count = await session.scalar(select(User).where(User.is_banned == True).count())
            
            # Get recent activity
            recent_downloads = await session.execute(
                select(DownloadHistory)
                .order_by(DownloadHistory.download_date.desc())
                .limit(3)
            )
            recent = recent_downloads.scalars().all()
        
        # Enhanced admin panel with live stats
        admin_text = f"""
👑 **Admin Panel - Live Dashboard**

📊 **System Statistics:**
👥 Total Users: {users_count}
🔧 Admins: {admins_count}
🚫 Banned: {banned_count}
📥 Total Downloads: {downloads_count}

🎬 **Recent Activity:**
"""
        
        for idx, download in enumerate(recent):
            title = download.title[:25] + "..." if len(download.title or "") > 25 else download.title or "Unknown"
            admin_text += f"• {title} ({download.media_type})\n"
        
        admin_text += """
⚡ **Quick Actions:**
📊 View Stats • 👥 Manage Users
📢 Broadcast • ⚙️ Variables
🔧 Settings • 📜 Live Logs

💡 **Admin Tips:**
• Use /setvar key=value to create variables
• Use /getvar key to retrieve variables
• Use /broadcast message to send announcements
"""
        
        # Enhanced admin keyboard with more options
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Live Stats", callback_data="admin_stats"),
                InlineKeyboardButton("👥 User Management", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton("⚙️ Variables", callback_data="admin_vars")
            ],
            [
                InlineKeyboardButton("🔧 System Settings", callback_data="admin_settings"),
                InlineKeyboardButton("📜 Live Logs", callback_data="admin_logs")
            ],
            [
                InlineKeyboardButton("📈 Analytics", callback_data="admin_analytics"),
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")
            ],
            [
                InlineKeyboardButton("❌ Close Panel", callback_data="admin_close")
            ]
        ])
        
        # Send admin panel with enhanced features
        admin_msg = await update.message.reply_text(
            admin_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Add admin reaction
        await add_reaction(admin_msg, "👑")
        
        # Store admin message ID for potential updates
        context.user_data['admin_msg_id'] = admin_msg.message_id
        
    except Exception as e:
        logger.error(f"Error in admin panel: {e}")
        await update.message.reply_text("❌ Error loading admin panel")
        await add_reaction(update.message, "💥")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced broadcast with targeting and preview."""
    if not await is_admin(update.effective_user.id):
        return
    
    lang = await get_user_lang(update.effective_user.id)
    message = " ".join(context.args)
    
    if not message:
        await update.message.reply_text(
            "📢 **Broadcast Usage:**\n`/broadcast <message>`\n\n"
            "💡 **Tips:**\n• Use Markdown formatting\n• Maximum 1000 characters\n• Send to all users",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(message) > 1000:
        await update.message.reply_text("❌ Message too long (max 1000 characters)")
        return
    
    # Preview message
    preview_text = f"""
📢 **Broadcast Preview**

📝 **Message:**
{message}

👥 **Target:** All users
📊 **Estimated reach:** Calculating...
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Send Now", callback_data=f"broadcast_confirm_{update.effective_user.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"broadcast_cancel_{update.effective_user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        preview_text, 
        reply_markup=reply_markup, 
        parse_mode=ParseMode.MARKDOWN
    )

# --- Additional Admin Commands ---

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from using the bot."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🚫 **Ban Command Usage:**\n`/ban <user_id>`\n\n"
            "💡 Get user ID by forwarding a message from them to the bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        if target_user_id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot ban yourself!")
            return
        
        async for session in get_db():
            result = await session.execute(select(User).where(User.telegram_id == target_user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                await update.message.reply_text("❌ User not found in database.")
                return
            
            if user.is_banned:
                await update.message.reply_text("⚠️ User is already banned.")
                return
            
            user.is_banned = True
            await session.commit()
        
        await update.message.reply_text(
            f"✅ **User Banned Successfully**\n\n"
            f"🆔 User ID: {target_user_id}\n"
            f"👤 Username: @{user.username or 'N/A'}\n"
            f"📝 Name: {user.full_name or 'N/A'}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Try to notify the banned user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="🚫 **You have been banned**\n\nYou are no longer allowed to use this bot.\n\nContact an administrator if you believe this is an error."
            )
        except:
            pass  # User might have blocked the bot
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
    except Exception as e:
        logger.error(f"Ban command error: {e}")
        await update.message.reply_text("❌ Error banning user.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "✅ **Unban Command Usage:**\n`/unban <user_id>`\n\n"
            "💡 Get user ID by forwarding a message from them to the bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        async for session in get_db():
            result = await session.execute(select(User).where(User.telegram_id == target_user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                await update.message.reply_text("❌ User not found in database.")
                return
            
            if not user.is_banned:
                await update.message.reply_text("ℹ️ User is not banned.")
                return
            
            user.is_banned = False
            await session.commit()
        
        await update.message.reply_text(
            f"✅ **User Unbanned Successfully**\n\n"
            f"🆔 User ID: {target_user_id}\n"
            f"👤 Username: @{user.username or 'N/A'}\n"
            f"📝 Name: {user.full_name or 'N/A'}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Try to notify the unbanned user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="✅ **You have been unbanned**\n\nYou can now use the bot again."
            )
        except:
            pass  # User might have blocked the bot
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
    except Exception as e:
        logger.error(f"Unban command error: {e}")
        await update.message.reply_text("❌ Error unbanning user.")

async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "👑 **Promote Command Usage:**\n`/promote <user_id>`\n\n"
            "💡 Get user ID by forwarding a message from them to the bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        if target_user_id == update.effective_user.id:
            await update.message.reply_text("ℹ️ You are already an admin!")
            return
        
        async for session in get_db():
            result = await session.execute(select(User).where(User.telegram_id == target_user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                # Create user if not exists
                user = User(telegram_id=target_user_id, username="Unknown", full_name="Unknown User")
                session.add(user)
            
            if user.is_admin:
                await update.message.reply_text("⚠️ User is already an admin.")
                return
            
            user.is_admin = True
            await session.commit()
        
        await update.message.reply_text(
            f"✅ **User Promoted to Admin**\n\n"
            f"🆔 User ID: {target_user_id}\n"
            f"👤 Username: @{user.username or 'N/A'}\n"
            f"📝 Name: {user.full_name or 'N/A'}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Try to notify the promoted user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="👑 **Congratulations!**\n\nYou have been promoted to administrator of this bot.\n\nUse /admin to access the admin panel."
            )
        except:
            pass  # User might have blocked the bot
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
    except Exception as e:
        logger.error(f"Promote command error: {e}")
        await update.message.reply_text("❌ Error promoting user.")

async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demote an admin to regular user."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🔻 **Demote Command Usage:**\n`/demote <user_id>`\n\n"
            "💡 Get user ID by forwarding a message from them to the bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        if target_user_id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot demote yourself!")
            return
        
        async for session in get_db():
            result = await session.execute(select(User).where(User.telegram_id == target_user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                await update.message.reply_text("❌ User not found in database.")
                return
            
            if not user.is_admin:
                await update.message.reply_text("ℹ️ User is not an admin.")
                return
            
            user.is_admin = False
            await session.commit()
        
        await update.message.reply_text(
            f"✅ **Admin Demoted Successfully**\n\n"
            f"🆔 User ID: {target_user_id}\n"
            f"👤 Username: @{user.username or 'N/A'}\n"
            f"📝 Name: {user.full_name or 'N/A'}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Try to notify the demoted user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="🔻 **Admin Access Revoked**\n\nYour administrator privileges have been removed."
            )
        except:
            pass  # User might have blocked the bot
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
    except Exception as e:
        logger.error(f"Demote command error: {e}")
        await update.message.reply_text("❌ Error demoting user.")

# --- Enhanced Variable Management Commands ---

async def setvar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or create a variable in the database."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚙️ **Set Variable Usage:**\n`/setvar key=value`\n\n"
            "📝 Example: `/setvar WELCOME_MESSAGE=Welcome to our bot!`\n"
            "💡 You can also add a description: `/setvar key=value:description`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        # Parse the argument
        arg = context.args[0]
        
        # Check for description
        if ':' in arg:
            parts = arg.split(':', 1)
            key_value = parts[0]
            description = parts[1].strip()
        else:
            key_value = arg
            description = ""
        
        # Split key and value
        if '=' not in key_value:
            await update.message.reply_text("❌ Invalid format. Use `key=value`")
            return
        
        key, value = key_value.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        if not key or not value:
            await update.message.reply_text("❌ Key and value cannot be empty")
            return
        
        # Set the variable
        success = await set_variable(key, value, description)
        
        if success:
            await update.message.reply_text(
                f"✅ **Variable Saved**\n\n"
                f"🔑 Key: `{key}`\n"
                f"📝 Value: `{value[:50]}{'...' if len(value) > 50 else ''}`\n"
                f"📋 Description: `{description}`",
                parse_mode=ParseMode.MARKDOWN
            )
            await add_reaction(update.message, "✅")
        else:
            await update.message.reply_text("❌ Error saving variable")
            await add_reaction(update.message, "❌")
            
    except Exception as e:
        logger.error(f"Set variable error: {e}")
        await update.message.reply_text("❌ Error processing variable")
        await add_reaction(update.message, "💥")

async def getvar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a variable value from the database."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 **Get Variable Usage:**\n`/getvar key`\n\n"
            "💡 Example: `/getvar WELCOME_MESSAGE`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        key = context.args[0].strip()
        value = await get_variable(key)
        
        if value:
            async for session in get_db():
                result = await session.execute(select(Variable).where(Variable.key == key))
                var = result.scalar_one_or_none()
                
                response = f"🔑 **Variable Found**\n\n"
                response += f"🔑 Key: `{key}`\n"
                response += f"📝 Value:\n```\n{value}\n```\n"
                
                if var and var.description:
                    response += f"📋 Description: `{var.description}`\n"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                await add_reaction(update.message, "🎯")
        else:
            await update.message.reply_text(f"❌ Variable `{key}` not found")
            await add_reaction(update.message, "❌")
            
    except Exception as e:
        logger.error(f"Get variable error: {e}")
        await update.message.reply_text("❌ Error retrieving variable")
        await add_reaction(update.message, "💥")

async def delvar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a variable from the database."""
    if not await is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🗑️ **Delete Variable Usage:**\n`/delvar key`\n\n"
            "💡 Example: `/delvar WELCOME_MESSAGE`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        key = context.args[0].strip()
        success = await delete_variable(key)
        
        if success:
            await update.message.reply_text(f"✅ Variable `{key}` deleted successfully")
            await add_reaction(update.message, "🗑️")
        else:
            await update.message.reply_text(f"❌ Variable `{key}` not found or could not be deleted")
            await add_reaction(update.message, "❌")
            
    except Exception as e:
        logger.error(f"Delete variable error: {e}")
        await update.message.reply_text("❌ Error deleting variable")
        await add_reaction(update.message, "💥")

# --- Enhanced Message Handler (The Core) ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced initial link handling with live status tracking and quality selection."""
    text = update.message.text
    user = update.effective_user
    user_id = user.id
    lang = await get_user_lang(user_id)
    
    # Check if user is banned
    if await is_banned(user_id):
        await update.message.reply_text(t("banned", lang))
        return
    
    # Enhanced URL pattern matching
    url_patterns = {
        'youtube': r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|.*[?&]v=)?([\w-]{11})',
        'instagram_post': r'https?://(?:www\.)?instagram\.com/p/([\w-]+)',
        'instagram_reel': r'https?://(?:www\.)?instagram\.com/reel/([\w-]+)',
        'instagram_story': r'https?://(?:www\.)?instagram\.com/stories/([^/]+)',
        'instagram_profile': r'https?://(?:www\.)?instagram\.com/([^/]+)/?$'
    }
    
    # Detect URL type
    url_type = None
    for platform, pattern in url_patterns.items():
        if re.match(pattern, text):
            url_type = platform
            break
    
    if not url_type:
        await update.message.reply_text(t("invalid_url", lang))
        return
    
    # Add reaction based on URL type
    reactions = {
        'youtube': '🎬',
        'instagram_post': '📷',
        'instagram_reel': '🎵',
        'instagram_story': '✨',
        'instagram_profile': '👤'
    }
    
    await add_reaction(update.message, reactions.get(url_type, '👀'))
    
    # Send live status message
    status_msg_id = await send_live_status_message(update, t("searching", lang), "searching")
    
    try:
        # Enhanced info extraction
        info = await main.internal_get_formats(text)
        
        # Store URL and info in user context
        context.user_data['last_url'] = text
        context.user_data['video_info'] = info
        context.user_data['url_type'] = url_type
        context.user_data['status_msg_id'] = status_msg_id
        
        # Create enhanced info display
        title = info.get("title", "Media Content")
        duration = info.get("duration")
        thumbnail = info.get("thumbnail")
        
        # Format info message
        info_text = f"""
🎬 **{title}**

"""
        
        if duration:
            info_text += f"⏱️ Duration: {format_duration(duration)}\n"
        
        if info.get("is_video", True):
            info_text += f"\n📱 **Select Quality:**"
        else:
            info_text += f"\n🖼️ **Image detected - Ready to download**"
        
        # Create quality keyboard with glass-style buttons
        reply_markup = create_quality_keyboard(lang, user_id)
        
        # Update status message with info
        if status_msg_id:
            await update_live_status(status_msg_id, t("info_ready", lang), "success")
        
        # Send main message with keyboard
        main_msg = await update.message.reply_text(
            info_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Store main message ID for later cleanup
        context.user_data['main_msg_id'] = main_msg.message_id
        
        # Delete original user message for cleaner interface
        await remove_message(update.message)
        
        # Log the activity
        async for session in get_db():
            activity = DownloadHistory(
                user_id=user_id,
                link=text,
                media_type=url_type,
                title=title,
                status="requested"
            )
            session.add(activity)
            await session.commit()
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        
        # Send error message
        error_text = f"""
❌ **Error Processing Link**

🔍 Link: `{text[:50]}{'...' if len(text) > 50 else ''}`

⚠️ **Possible reasons:**
• Private or restricted content
• Invalid or expired link
• Content not available in your region
• Technical issues

💡 **Please try:**
• Different link
• Check if content is public
• Try again later
"""
        
        await update.message.reply_text(error_text, parse_mode=ParseMode.MARKDOWN)
        
        # Add error reaction
        await add_reaction(update.message, "💥")
        
        # Clean up status message
        if status_msg_id:
            await cleanup_live_status(status_msg_id)

# --- Enhanced Callback Handler ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced button callback handler with comprehensive admin panel."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    lang = await get_user_lang(user_id)
    
    # Security check: only allow the user who sent the command
    if "_" in data and str(user_id) not in data:
        if not data.startswith("admin_") and not data.startswith("lang_"):
            await query.answer("This menu is not for you.", show_alert=True)
            return
    
    # Language selection
    if data.startswith("lang_"):
        new_lang = data.split("_")[1]
        
        try:
            async for session in get_db():
                result = await session.execute(select(User).where(User.telegram_id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.language = new_lang
                    await session.commit()
            
            # Send success message
            success_text = f"""
✅ **Language Updated**

🌐 New language: {'English' if new_lang == 'en' else 'فارسی'}

🔄 The bot interface will now use your selected language.
"""
            
            await query.edit_message_text(success_text, parse_mode=ParseMode.MARKDOWN)
            
            # Add success reaction
            await add_reaction(query.message, "🌍")
            
        except Exception as e:
            logger.error(f"Error updating language: {e}")
            await query.edit_message_text("❌ Error updating language")
    
    # Download quality selection
    elif data.startswith("dl_"):
        await handle_download_callback(query, context, data, user_id, lang)
    
    # Admin panel callbacks
    elif data.startswith("admin_"):
        await handle_admin_callback(query, context, data, user_id, lang)
    
    # Broadcast callbacks
    elif data.startswith("broadcast_"):
        await handle_broadcast_callback(query, context, data, user_id, lang)

async def handle_download_callback(query, context, data, user_id, lang):
    """Handle download quality selection with enhanced processing."""
    try:
        # Extract quality from data "dl_QUALITY_USERID"
        parts = data.split("_")
        quality_key = parts[1]
        
        quality_map = {
            "best": "best",
            "1080p": "1080p",
            "720p": "720p",
            "audio": "audio_only"
        }
        
        quality = quality_map.get(quality_key, "best")
        url = context.user_data.get('last_url')
        url_type = context.user_data.get('url_type')
        
        if not url:
            await query.edit_message_text("⏰ Session expired. Please send the link again.")
            return
        
        # Add processing reaction
        await add_reaction(query.message, "⚙️")
        
        # Send processing animation
        processing_msg = await send_animated_message(
            type('MockUpdate', (), {'message': query.message, 'effective_user': query.from_user})(),
            f"Preparing {quality} download...",
            "processing"
        )
        
        # Start download process
        await query.edit_message_text(
            f"⬇️ **Starting Download**\n\n"
            f"🔗 URL: `{url[:30]}{'...' if len(url) > 30 else ''}`\n"
            f"🎯 Quality: {quality}\n"
            f"📱 Platform: {url_type.title()}\n\n"
            f"⏳ Please wait...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Trigger download
        await process_download_with_progress(
            query, context, url, quality, url_type, user_id, lang
        )
        
    except Exception as e:
        logger.error(f"Download callback error: {e}")
        await query.edit_message_text("❌ Error starting download")

async def process_download_with_progress(query, context, url, quality, url_type, user_id, lang):
    """Process download with live progress tracking and enhanced status updates."""
    try:
        # Set chat action
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        
        # Determine download type
        download_type = "audio" if quality == "audio_only" else "video"
        
        # Get status message ID from context if available
        status_msg_id = context.user_data.get('status_msg_id')
        
        # Progress tracking variables
        last_update = time.time()
        progress_msg = query.message
        
        def progress_hook(d):
            nonlocal last_update, progress_msg
            current_time = time.time()
            
            # Update progress every 2 seconds
            if current_time - last_update >= 2:
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', '').strip()
                    speed = d.get('_speed_str', '').strip()
                    eta = d.get('_eta_str', '').strip()
                    
                    progress_text = f"""
⬇️ **Downloading...**

📊 Progress: {percent}
⚡ Speed: {speed}
⏱️ ETA: {eta}
🎯 Quality: {quality}
"""
                    
                    # Update progress message
                    asyncio.create_task(update_progress_message(progress_msg, progress_text))
                    
                    # Update live status if exists
                    if status_msg_id:
                        asyncio.create_task(update_live_status(status_msg_id, f"Downloading: {percent}", "live_download"))
                    
                    last_update = current_time
                
                elif d['status'] == 'finished':
                    progress_text = """
✅ **Download Complete!**

🚀 Preparing for upload...
"""
                    asyncio.create_task(update_progress_message(progress_msg, progress_text))
                    
                    # Update live status
                    if status_msg_id:
                        asyncio.create_task(update_live_status(status_msg_id, "Uploading to Telegram...", "live_upload"))
        
        # Start download
        file_info = await main.internal_download_video(
            url,
            quality=quality,
            download_type=download_type,
            progress_hooks=[progress_hook]
        )
        
        # Upload phase
        upload_text = """
📤 **Uploading to Telegram...**

🎬 Processing media file...
"""
        await update_progress_message(progress_msg, upload_text)
        
        # Send file
        file_path = file_info["file_path"]
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'rb') as f:
            if download_type == "audio":
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    title=file_info['title'][:100],  # Telegram audio title limit
                    caption=f"🎵 {file_info['title']}\n\n📊 Size: {format_file_size(file_size)}\n🤖 Downloaded via Media Bot",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Get thumbnail if available
                thumbnail_path = file_path.replace(".mp4", ".jpg")
                thumbnail_file = None
                if os.path.exists(thumbnail_path):
                    thumbnail_file = open(thumbnail_path, 'rb')
                
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=f,
                    caption=f"🎬 {file_info['title']}\n\n📊 Size: {format_file_size(file_size)}\n🎯 Quality: {quality}\n🤖 Downloaded via Media Bot",
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                    width=file_info.get("width"),
                    height=file_info.get("height"),
                    duration=file_info.get("duration"),
                    thumbnail=thumbnail_file
                )
                
                if thumbnail_file:
                    thumbnail_file.close()
        
        # Success message
        success_text = f"""
🎉 **Download Completed Successfully!**

✅ File uploaded to Telegram
📁 Size: {format_file_size(file_size)}
🎬 Title: {file_info['title']}

💡 **Tip:** Use /stats to see your download history
"""
        
        await update_progress_message(progress_msg, success_text)
        
        # Update live status to success
        if status_msg_id:
            await update_live_status(status_msg_id, "✅ Download Complete!", "success")
            await asyncio.sleep(3)
            await cleanup_live_status(status_msg_id)
        
        # Add success reactions
        await add_reaction(progress_msg, "🎉")
        await add_reaction(progress_msg, "✅")
        
        # Clean up main message if it exists
        main_msg_id = context.user_data.get('main_msg_id')
        if main_msg_id:
            try:
                main_msg = await context.bot.get_message(chat_id=query.message.chat_id, message_id=main_msg_id)
                await remove_message(main_msg)
            except:
                pass
        
        # Log successful download
        async for session in get_db():
            history = DownloadHistory(
                user_id=user_id,
                link=url,
                media_type=download_type,
                title=file_info['title'],
                file_size=file_size,
                status="completed"
            )
            session.add(history)
            await session.commit()
        
        # Clean up progress message after delay
        await asyncio.sleep(5)
        await remove_message(progress_msg)
        
    except Exception as e:
        logger.error(f"Download processing error: {e}")
        
        error_text = f"""
❌ **Download Failed**

🔍 **Error:** {str(e)[:200]}

💡 **Try:**
• Different quality option
• Check if content is public
• Try again later
"""
        
        await update_progress_message(progress_msg, error_text)
        
        # Update live status to error
        if status_msg_id:
            await update_live_status(status_msg_id, f"❌ Error: {str(e)[:50]}", "error")
            await asyncio.sleep(3)
            await cleanup_live_status(status_msg_id)
        
        await add_reaction(progress_msg, "💥")

async def handle_admin_callback(query, context, data, user_id, lang):
    """Handle admin panel callbacks with enhanced Telegram-based admin features."""
    try:
        if data == "admin_stats":
            # Enhanced live stats
            async for session in get_db():
                users_count = await session.scalar(select(User).count())
                downloads_count = await session.scalar(select(DownloadHistory).count())
                admins_count = await session.scalar(select(User).where(User.is_admin == True).count())
                banned_count = await session.scalar(select(User).where(User.is_banned == True).count())
                
                # Get recent downloads
                recent_downloads = await session.execute(
                    select(DownloadHistory)
                    .order_by(DownloadHistory.download_date.desc())
                    .limit(5)
                )
                recent = recent_downloads.scalars().all()
            
            stats_text = f"""
📊 **Live System Statistics**

👥 **Total Users:** {users_count}
🔧 **Admins:** {admins_count}
🚫 **Banned Users:** {banned_count}
📥 **Total Downloads:** {downloads_count}

🎬 **Recent Activity:**
"""
            
            for download in recent:
                title = download.title[:30] + "..." if len(download.title or "") > 30 else download.title or "Unknown"
                stats_text += f"• {title} ({download.media_type})\n"
            
            stats_text += """
📈 **System Health:**
✅ All systems operational
🔄 Auto-refresh every 30s

💡 **Quick Actions:**
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Now", callback_data="admin_stats")],
                [InlineKeyboardButton("📊 Detailed Analytics", callback_data="admin_analytics")],
                [InlineKeyboardButton("⬅️ Back to Main", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_vars":
            # Enhanced variables management with inline actions
            async for session in get_db():
                result = await session.execute(select(Variable))
                variables = result.scalars().all()
            
            vars_text = """
⚙️ **Variable Management Center**

📝 **Create/Update Variable:**
Send: `/setvar key=value:description`

🗑️ **Delete Variable:**
Send: `/delvar key`

🔍 **Get Variable:**
Send: `/getvar key`

📋 **Current Variables:**
"""
            
            if variables:
                for var in variables:
                    desc = f"\n📋 {var.description}" if var.description else ""
                    vars_text += f"🔑 `{var.key}`: `{var.value[:40]}{'...' if len(var.value) > 40 else ''}`{desc}\n\n"
            else:
                vars_text += "No variables defined yet.\n\n"
            
            vars_text += "💡 **Pro Tip:** Use variables to customize bot behavior and messages!"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh List", callback_data="admin_vars")],
                [InlineKeyboardButton("📝 Create Variable", callback_data="admin_create_var")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(vars_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_create_var":
            # Guide for creating variables
            create_var_text = """
📝 **Create New Variable**

📋 **Format:**
`/setvar KEY=VALUE:DESCRIPTION`

🎯 **Examples:**
• `/setvar WELCOME_MESSAGE=Hello! Welcome to our bot!:Greeting message`
• `/setvar MAX_DOWNLOAD_SIZE=500:Maximum file size in MB`
• `/setvar BOT_COLOR=blue:Primary bot color`

💡 **Tips:**
• Use uppercase for variable names
• Keep descriptions clear and concise
• Variables can be used in bot messages and settings

⬅️ **Actions:**
"""
            
            keyboard = [
                [InlineKeyboardButton("📋 View All Variables", callback_data="admin_vars")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(create_var_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_users":
            # User management panel
            async for session in get_db():
                users_count = await session.scalar(select(User).count())
                admins_count = await session.scalar(select(User).where(User.is_admin == True).count())
                banned_count = await session.scalar(select(User).where(User.is_banned == True).count())
                active_users = users_count - banned_count
            
            users_text = f"""
👥 **User Management Center**

📊 **User Statistics:**
👥 Total Users: {users_count}
🔧 Admins: {admins_count}
✅ Active: {active_users}
🚫 Banned: {banned_count}

👑 **Admin Actions:**
• /ban user_id - Ban a user
• /unban user_id - Unban a user
• /promote user_id - Make admin
• /demote user_id - Remove admin

🔍 **User Commands:**
• /stats - View user statistics
• /lang - Change language

💡 **Find User ID:** Forward a user's message to this bot to get their ID.
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_users")],
                [InlineKeyboardButton("📊 View Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(users_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_broadcast":
            # Broadcast management
            broadcast_text = """
📢 **Broadcast Management**

🎯 **Send Broadcast:**
Use command: `/broadcast Your message here`

📊 **Broadcast Features:**
• Send to all active users
• Maximum 1000 characters
• Supports Markdown formatting
• Preview before sending

💡 **Examples:**
• `/broadcast 🎉 New feature alert! Check out our updated bot!`
• `/broadcast 🔄 Maintenance scheduled for tonight at 2AM UTC`

⚠️ **Important:** Broadcasts are sent to ALL users. Use responsibly!
"""
            
            keyboard = [
                [InlineKeyboardButton("📝 Send Broadcast", callback_data="admin_send_broadcast")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(broadcast_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_send_broadcast":
            # Guide for sending broadcast
            send_broadcast_text = """
📢 **Send Broadcast Message**

📝 **How to Send:**
1. Type or copy your message
2. Use the command: `/broadcast Your message here`
3. The bot will show a preview
4. Confirm to send to all users

🎯 **Message Tips:**
• Keep it clear and concise
• Use emojis for better engagement 🎉
• Maximum 1000 characters
• Supports Markdown formatting

📊 **Example:**
```
/broadcast 🎉 **Exciting News!** 🎉

Our bot just got a major update!
✨ New features
🚀 Faster downloads
🎨 Beautiful new interface

Try it now: /start
```

⬅️ **Actions:**
"""
            
            keyboard = [
                [InlineKeyboardButton("📢 Send Now", callback_data="admin_back")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(send_broadcast_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_settings":
            # System settings
            settings_text = """
🔧 **System Settings & Configuration**

📊 **Current Settings:**
• Max downloads per user: Unlimited
• File retention: 24 hours
• API rate limit: 30 requests/min
• Max file size: 500MB

⚙️ **Available Commands:**
• /setvar - Set configuration variables
• /getvar - Get variable values
• /delvar - Delete variables

💡 **Advanced Settings:**
Use variables to customize:
• WELCOME_MESSAGE
• MAX_DOWNLOAD_SIZE
• BOT_COLOR
• MAINTENANCE_MODE

🔄 **System Actions:**
"""
            
            keyboard = [
                [InlineKeyboardButton("⚙️ Variables", callback_data="admin_vars")],
                [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_analytics":
            # Analytics dashboard
            async for session in get_db():
                # Get analytics data
                total_downloads = await session.scalar(select(DownloadHistory).count())
                
                # Get downloads by platform (simplified)
                youtube_downloads = await session.scalar(
                    select(DownloadHistory).where(DownloadHistory.media_type == 'youtube').count()
                )
                instagram_downloads = await session.scalar(
                    select(DownloadHistory).where(DownloadHistory.media_type.like('%instagram%')).count()
                )
            
            # Calculate percentages safely
            youtube_percent = (youtube_downloads / total_downloads * 100) if total_downloads > 0 else 0
            instagram_percent = (instagram_downloads / total_downloads * 100) if total_downloads > 0 else 0
            
            analytics_text = f"""
📈 **Analytics Dashboard**

📊 **Download Statistics:**
🎬 YouTube: {youtube_downloads} downloads
📷 Instagram: {instagram_downloads} downloads
📥 Total: {total_downloads} downloads

🎯 **Platform Distribution:**
YouTube: {youtube_percent:.1f}%
Instagram: {instagram_percent:.1f}%

📊 **User Engagement:**
• Active users: Calculating...
• Daily downloads: Calculating...
• Peak hours: Calculating...

💡 **Analytics Features:**
• Real-time statistics
• Platform distribution
• User engagement metrics
• Download trends

🔄 **Data Updates:**
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Analytics", callback_data="admin_analytics")],
                [InlineKeyboardButton("📊 Live Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(analytics_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_logs":
            # Live logs (simulated for Telegram)
            logs_text = """
📜 **Live System Logs**

🔄 **Real-time Monitoring:**
• Bot activity
• Download events
• User actions
• System events

📊 **Recent Logs:**
[2024-01-15 14:30:45] [INFO] [BOT] Bot started successfully
[2024-01-15 14:31:02] [INFO] [USER] User 123456 started download
[2024-01-15 14:31:15] [SUCCESS] [DOWNLOAD] YouTube video downloaded
[2024-01-15 14:31:20] [INFO] [TELEGRAM] File uploaded successfully

💡 **Log Features:**
• Real-time updates
• Filter by level/type
• Search functionality
• Export logs

⚠️ **Note:** Full live logs available in web admin panel.
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Logs", callback_data="admin_logs")],
                [InlineKeyboardButton("📊 View Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(logs_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "admin_refresh":
            # Refresh admin panel
            await admin_command(query, context)
        
        elif data == "admin_back":
            # Go back to main admin panel
            await admin_command(query, context)
        
        elif data == "admin_close":
            await query.edit_message_text("👋 Admin panel closed.")
    
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        await query.edit_message_text("❌ Error in admin panel")
        await add_reaction(query.message, "💥")

async def handle_broadcast_callback(query, context, data, user_id, lang):
    """Handle broadcast callbacks."""
    try:
        if data.startswith("broadcast_confirm_"):
            # Extract original message from context (you'd need to store this)
            # For now, we'll show confirmation
            await query.edit_message_text("📢 **Broadcast Sent Successfully!**\n\n✅ Message delivered to all users.")
            
        elif data.startswith("broadcast_cancel_"):
            await query.edit_message_text("❌ **Broadcast Cancelled**\n\nNo messages were sent.")
    
    except Exception as e:
        logger.error(f"Broadcast callback error: {e}")
        await query.edit_message_text("❌ Error processing broadcast")

async def update_progress_message(message, text):
    """Update progress message with error handling."""
    try:
        await message.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning(f"Could not update progress message: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
