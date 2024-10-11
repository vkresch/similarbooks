# Constants
DEBUG = False
QUERY_LIMIT = 20 if not DEBUG else 10_000_000

# NOTE: The endpoint and cookie session needs to be adjusted on the server
GRAPHQL_ENDPOINT = "http://127.0.0.1:8000/graphql"

GUTENBERG_PREFIX = "gb_"

MIN_SUMMARY_LENGTH = 400

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
  all_books (page: 1, per_page: 20, order_by: "-ratings_count",  filters: {0} ) {{
    edges {{
      node {{
        sha,
        title,
        author,
        ratings_count,
      }}
    }}
  }}
}}""".strip()

DETAILED_BOOK_QUERY = """
{{
  all_books (filters: {0} ) {{
    edges {{
      node {{
        sha,
        spider,
        summary,
        title,
        author,
        url,
        bmu_col,
        bmu_row,
        amazon_link,
        kindle_link,
      }}
    }}
  }}
}}""".strip()
