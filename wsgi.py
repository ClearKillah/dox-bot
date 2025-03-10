import os
import sys
import asyncio
import logging
import traceback
from bot import app, setup_handlers, setup_webhook, manual_set_webhook, get_webhook_info

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Set environment variables if not set
if not os.environ.get("WEBHOOK_URL"):
    os.environ["WEBHOOK_URL"] = "https://dox-bot-production.up.railway.app"
    logger.info(f"WEBHOOK_URL not set, using default: {os.environ['WEBHOOK_URL']}")

try:
    # Set up handlers
    logger.info("Setting up handlers...")
    setup_handlers()
    
    # Try both webhook setup methods
    logger.info("Setting up webhook using async method...")
    asyncio.run(setup_webhook())
    
    logger.info("Setting up webhook using manual method...")
    webhook_result = manual_set_webhook()
    logger.info(f"Manual webhook setup result: {webhook_result}")
    
    # Check webhook status
    webhook_info = get_webhook_info()
    logger.info(f"Current webhook info: {webhook_info}")
    
    logger.info("Bot setup completed successfully")
except Exception as e:
    logger.error(f"Error during bot setup: {e}")
    logger.error(traceback.format_exc())

# Export the Flask app
application = app 