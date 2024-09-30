# Constants
DEBUG = False
QUERY_LIMIT = 100 if not DEBUG else 10_000_000

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
  all_books (page: 1, per_page: 100, filters: {0} ) {{
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
        title,
        author,
      }}
    }}
  }}
}}""".strip()
