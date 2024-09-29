# Constants
DEBUG = False
QUERY_LIMIT = 50 if not DEBUG else 10_000_000

# NOTE: The endpoint and cookie session needs to be adjusted on the server
GRAPHQL_ENDPOINT = "http://127.0.0.1:8000/graphql"

GUTENBERG_PREFIX = "gb_"

IGNORE_FIELDS_FOR_FILTER = [
    "model",
    "document",
    "per_page",
    "page",
    "order_by",
    "filters",
]

BOOK_QUERY = """
{{
  all_books (order_by: '+title', page: 1, per_page: 50, filters: {0} ) {{
    edges {{
      node {{
        sha,
        title,
        author,
      }}
    }}
  }}
}}""".strip()

DETAILED_BOOK_QUERY = """
{{
  all_books (filters: {0} ) {{
    edges {{
      node {{
        book_id,
        sha,
        summary,
        date,
        title,
        author,
      }}
    }}
  }}
}}""".strip()
