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

def delete_webhook(drop_pending=True):
    """Delete webhook."""
    url = f"{TELEGRAM_API}/deleteWebhook?drop_pending_updates={str(drop_pending).lower()}"
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

def send_message(chat_id, text):
    """Send message to user."""
    url = f"{TELEGRAM_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, json=data)
    logger.info(f"Send message response: {response.text}")
    return response.json()

def main():
    """Run tests."""
    logger.info("Starting bot tests...")
    
    # Get bot info
    logger.info("Getting bot info...")
    me = get_me()
    
    # Delete webhook and drop pending updates
    logger.info("Deleting webhook and dropping pending updates...")
    delete_webhook(drop_pending=True)
    
    # Get updates
    logger.info("Getting updates...")
    updates = get_updates()
    
    # Set webhook
    logger.info("Setting webhook...")
    set_webhook()
    
    # Get webhook info
    logger.info("Getting webhook info...")
    webhook_info = get_webhook_info()
    
    # Try sending a test message to yourself if you know your chat_id
    # Uncomment and replace YOUR_CHAT_ID with your actual chat ID
    # send_message(YOUR_CHAT_ID, "Test message from bot")
    
    logger.info("Tests completed.")

if __name__ == "__main__":
    main() 