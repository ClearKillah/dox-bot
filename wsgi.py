import asyncio
from bot import app, setup_handlers, setup_webhook

# Set up handlers
setup_handlers()

# Set up webhook
asyncio.run(setup_webhook())

# Export the Flask app
application = app 