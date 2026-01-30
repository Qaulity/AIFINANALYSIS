"""Server entry point - loads .env before importing app to ensure settings are populated."""
import os
from dotenv import load_dotenv

# Load .env BEFORE importing app (order matters!)
load_dotenv(override=True)

# Clear cached settings so they reload with new env vars
from app.config import get_settings
get_settings.cache_clear()

# Now import and create the app
from app.main import create_app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
