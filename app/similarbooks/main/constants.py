# Constants
DEBUG = True
QUERY_LIMIT = 100 if not DEBUG else 10_000_000

# NOTE: The endpoint and cookie session needs to be adjusted on the server
GRAPHQL_ENDPOINT = "http://127.0.0.1:8000/graphql"

IGNORE_FIELDS_FOR_FILTER = [
    "model",
    "document",
    "per_page",
    "page",
    "order_by",
    "filters",
]
