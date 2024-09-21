import logging
from flask_caching import Cache
from app.similarbooks.main.constants import DEBUG

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if DEBUG else logging.INFO,
)

# Instantiate the cache
cache = Cache()
