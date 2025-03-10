import requests
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = "8039344227:AAEDCP_902a3r52JIdM9REqUyPx-p2IVtxA"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
WEBHOOK_URL = "https://dox-bot-production.up.railway.app"

def get_webhook_info():
    """Get webhook info."""
    url = f"{TELEGRAM_API}/getWebhookInfo"
    response = requests.get(url)
    logger.info(f"Webhook info response: {response.text}")
    return response.json()

def set_webhook():
    """Set webhook."""
    webhook_url = f"{WEBHOOK_URL}/telegram"
    url = f"{TELEGRAM_API}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    logger.info(f"Set webhook response: {response.text}")
    return response.json()

def delete_webhook():
    """Delete webhook."""
    url = f"{TELEGRAM_API}/deleteWebhook"
    response = requests.get(url)
    logger.info(f"Delete webhook response: {response.text}")
    return response.json()

def get_updates():
    """Get updates."""
    url = f"{TELEGRAM_API}/getUpdates"
    response = requests.get(url)
    logger.info(f"Get updates response: {response.text}")
    return response.json()

def get_me():
    """Get bot info."""
    url = f"{TELEGRAM_API}/getMe"
    response = requests.get(url)
    logger.info(f"Get me response: {response.text}")
    return response.json()

def main():
    """Run tests."""
    logger.info("Starting bot tests...")
    
    # Get bot info
    logger.info("Getting bot info...")
    me = get_me()
    
    # Delete webhook
    logger.info("Deleting webhook...")
    delete_webhook()
    
    # Get updates
    logger.info("Getting updates...")
    updates = get_updates()
    
    # Set webhook
    logger.info("Setting webhook...")
    set_webhook()
    
    # Get webhook info
    logger.info("Getting webhook info...")
    webhook_info = get_webhook_info()
    
    logger.info("Tests completed.")

if __name__ == "__main__":
    main() 