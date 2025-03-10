import asyncio
import logging
from bot import app, setup_handlers, setup_webhook

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    # Set up handlers
    setup_handlers()
    
    # Set up webhook
    asyncio.run(setup_webhook())
    
    logger.info("Bot setup completed successfully")
except Exception as e:
    logger.error(f"Error during bot setup: {e}")

# Export the Flask app
application = app 