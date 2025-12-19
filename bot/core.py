
import logging
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot import handlers
from database import get_db, Variable
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token placeholder - In production this should come from ENV or Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot_app = None # Global access to bot

async def load_token_from_db():
    """Try to load token from DB if not in ENV"""
    global BOT_TOKEN
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        async for session in get_db():
            result = await session.execute(select(Variable).where(Variable.key == "BOT_TOKEN"))
            var = result.scalar_one_or_none()
            if var:
                BOT_TOKEN = var.value
                logger.info("Bot token loaded from database.")
            else:
                logger.warning("Bot token not found in ENV or Database!")

async def run_bot():
    """Start the bot."""
    await load_token_from_db()
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("No valid BOT_TOKEN found. Bot will not start.")
        return

    global bot_app
    bot_app = Application.builder().token(BOT_TOKEN).build()
    application = bot_app

    # Register Handlers
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("lang", handlers.lang_command))
    application.add_handler(CommandHandler("stats", handlers.stats_command))
    
    # Admin Commands
    application.add_handler(CommandHandler("admin", handlers.admin_command))
    application.add_handler(CommandHandler("broadcast", handlers.broadcast_command))
    application.add_handler(CommandHandler("ban", handlers.ban_command))
    application.add_handler(CommandHandler("unban", handlers.unban_command))
    application.add_handler(CommandHandler("promote", handlers.promote_command))
    application.add_handler(CommandHandler("demote", handlers.demote_command))
    
    # Variable Management Commands
    application.add_handler(CommandHandler("setvar", handlers.setvar_command))
    application.add_handler(CommandHandler("getvar", handlers.getvar_command))
    application.add_handler(CommandHandler("delvar", handlers.delvar_command))
    
    # Message Handler for URLs
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    
    # Callback Query Handler for Buttons
    application.add_handler(CallbackQueryHandler(handlers.button_callback))

    # Error Handler
    application.add_error_handler(handlers.error_handler)

    # Initialize and start
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Bot started successfully.")
