# Constants
DEBUG = False
QUERY_LIMIT = 100 if not DEBUG else 10_000_000
MIN_DATE_DISPLAY = "7d"
NOTIFICATION_SLEEP = 10
MIN_BMU_PROPERTY_COUNT = 10
EST_MAINTENANCE_PRICE_PER_SQUARE_METER = (
    4.5  # Source: https://www.immobilienscout24.de/wissen/vermieten/hausgeldcheck.html
)
EST_MAINTENANCE_PRICE_OWNER_PART = (
    0.4  # https://matera.eu/artikel/hausgeld-umlagefaehig
)

# Default cashflow parameters
DEFAULT_INTEREST = 0.0353
DEFAULT_REPAYMENT = 0.02
DEFAULT_EQUITY = 0.2

UMATRIX_STR = "umatrix"
PRICE_MATRIX_STR = "price_matrix"
RENT_PRICE_MATRIX_STR = "rent_price_matrix"
PRICE_PER_SQUARE_METER_STR = "price_per_square_meter"
RENT_PRICE_PER_SQUARE_METER_STR = "rent_price_per_square_meter"
PRICE_PER_RENT_PRICE = "price_per_rent_price"
NODE_COUNT = "node_count"
CASHFLOW = "cashflow"
TOTAL_PRICE = "total_price"
MAINTENANCE_PRICE = "maintenance_price"
UNITS = {
    "square_meter": "m²",
    "energy_consumption": "kWh/(m²·a)",
    "currency": "€",
}
UNITS.update(
    {
        PRICE_MATRIX_STR: UNITS["currency"],
        RENT_PRICE_MATRIX_STR: UNITS["currency"],
        PRICE_PER_SQUARE_METER_STR: f'{UNITS["currency"]}/{UNITS["square_meter"]}',
        RENT_PRICE_PER_SQUARE_METER_STR: f'{UNITS["currency"]}/{UNITS["square_meter"]}',
        CASHFLOW: UNITS["currency"],
        TOTAL_PRICE: UNITS["currency"],
        MAINTENANCE_PRICE: UNITS["currency"],
    }
)

BUNDESLAENDER_LIST = [
    "all",
    "bl-schleswig-holstein",
    "bl-mecklenburg-vorpommern",
    "hamburg",
    "bremen",
    "bl-nordrhein-westfalen",
    "bl-niedersachsen",
    "bl-sachsen-anhalt",
    "bl-sachsen",
    "bl-thueringen",
    "bl-hessen",
    "bl-rheinland-pfalz",
    "bl-brandenburg",
    "bl-saarland",
    "berlin",
    "bl-baden-wuerttemberg",
    "bl-bayern",
]

DECIMAL_PRECISION = {
    PRICE_MATRIX_STR: 2,
    RENT_PRICE_MATRIX_STR: 2,
    PRICE_PER_SQUARE_METER_STR: 2,
    RENT_PRICE_PER_SQUARE_METER_STR: 2,
    CASHFLOW: 2,
    TOTAL_PRICE: 2,
    MAINTENANCE_PRICE: 2,
    UMATRIX_STR: 4,
    "energy_consumption": 2,
    "square_meter": 2,
    "lat": 4,
    "lon": 4,
}

# NOTE: The endpoint and cookie session needs to be adjusted on the server
GRAPHQL_ENDPOINT = "http://127.0.0.1:8000/graphql"
OPENPLZAPI_LOCALITIES = "https://openplzapi.org/de/Localities"

MODEL_NAMES = {
    "lat_lon_sq": ["immo_id", "lat", "lon", "square_meter"],
    "lat_lon_sq_bj": ["immo_id", "lat", "lon", "square_meter", "year_of_construction"],
    "lat_lon_sq_ro": ["immo_id", "lat", "lon", "square_meter", "rooms"],
    "lat_lon_sq_bj_ro": [
        "immo_id",
        "lat",
        "lon",
        "square_meter",
        "year_of_construction",
        "rooms",
    ],
    # "lat_lon_sq_bj_ro_ec": ["immo_id", "lat", "lon", "square_meter", "year_of_construction", "rooms", "energy_consumption"], TODO: In progress
}
MODEL_QUERIES = {
    "lat_lon_sq": "{square_meter_gt: 0, square_meter_lt: 10000, lat_exists: true, lon_exists: true, lat_lt: 56, lat_gt: 47,  lon_lt: 16, lon_gt: 5}",
    "lat_lon_sq_bj": '{year_of_construction_gt: "0001-01-01T00:00:00.000000", square_meter_gt: 0, square_meter_lt: 10000, lat_exists: true, lon_exists: true, lat_lt: 56, lat_gt: 47,  lon_lt: 16, lon_gt: 5}',
    "lat_lon_sq_ro": "{square_meter_gt: 0, square_meter_lt: 10000, rooms_gt: 0, lat_exists: true, lon_exists: true, lat_lt: 56, lat_gt: 47,  lon_lt: 16, lon_gt: 5}",
    "lat_lon_sq_bj_ro": '{year_of_construction_gt: "0001-01-01T00:00:00.000000", square_meter_gt: 0, square_meter_lt: 10000, rooms_gt: 0, lat_exists: true, lon_exists: true, lat_lt: 56, lat_gt: 47,  lon_lt: 16, lon_gt: 5}',
    # "lat_lon_sq_bj_ro_ec": ["immo_id", "lat", "lon", "square_meter", "year_of_construction", "rooms", "energy_consumption"], TODO: In progress
}
IGNORE_FIELDS_FOR_FILTER = [
    "model",
    "document",
    "per_page",
    "page",
    "order_by",
    "equity_percentage",
    "interest",
    "repayment",
    "filters",
]

KAUFEN_QUERY = """
{{
  {0} (order_by: '{1}', page: {2}, per_page: 100, equity_percentage: {6}, interest: {7}, repayment: {8},  filters: {3} ) {{
    edges {{
      node {{
        immo_id,
        uptime_date,
        title,
        square_meter,
        year_of_construction,
        city,
        price,
        price_per_square_meter,
        som_model_price,
        som_model_percentage,
        cashflow,
        roi
      }}
    }}
  }}
  {4} (equity_percentage: {6}, interest: {7}, repayment: {8}, filters: {3})
  {5} (equity_percentage: {6}, interest: {7}, repayment: {8}, filters: {3}) {{
    edges {{
      node {{
        avg_price_per_square_meter
        avg_rent_per_square_meter
      }}
    }}
  }}
}}""".strip()

CACHED_KAUFEN_QUERY = """
{{
  {0} (order_by: '{1}', page: {2}, per_page: 100, equity_percentage: {4}, interest: {5}, repayment: {6},  filters: {3} ) {{
    edges {{
      node {{
        immo_id,
        uptime_date,
        title,
        square_meter,
        year_of_construction,
        city,
        price,
        price_per_square_meter,
        som_model_price,
        som_model_percentage,
        cashflow,
        roi
      }}
    }}
  }}
}}""".strip()

MIETEN_QUERY = """
{{
  {0} (order_by: '{1}', page: {2}, per_page: 100, filters: {3} ) {{
    edges {{
      node {{
        immo_id,
        uptime_date,
        title,
        square_meter,
        year_of_construction,
        city,
        rent_price,
        rent_per_square_meter,
        som_model_rent,
        som_model_percentage,
      }}
    }}
  }}
  {4} (filters: {3})
  {5} (filters: {3}) {{
    edges {{
      node {{
        avg_price_per_square_meter
        avg_rent_per_square_meter
      }}
    }}
  }}
}}""".strip()

CACHED_MIETEN_QUERY = """
{{
  {0} (order_by: '{1}', page: {2}, per_page: 100, filters: {3} ) {{
    edges {{
      node {{
        immo_id,
        uptime_date,
        title,
        square_meter,
        year_of_construction,
        city,
        rent_price,
        rent_per_square_meter,
        som_model_rent,
        som_model_percentage,
      }}
    }}
  }}
}}""".strip()

BASIC_QUERY = """
{{
  {0} ( filters: {1}, equity_percentage: {2}, interest: {3}, repayment: {4} ){{
    edges {{
      node {{
        immo_id,
        spider,
        uptime_date,
        title,
        url,
        action,
        square_meter,
        lat,
        lon,
        city,
        rooms,
        year_of_construction,
        price,
        price_per_square_meter,
        maintenance_price,
        rent_price,
        rent_per_square_meter,
        most_recent_price_change,
        som_model_rent,
        som_model_price,
        som_model_percentage,
        cashflow,
        roi
      }}
    }}
  }}
}}""".strip()

COLUMN_NAMES = {
    "immo_id": str,
    "title": str,
    "square_meter": float,
    "year_of_construction": int,
    "city": str,
    "location": str,
    "rent_price": float,
    "price": float,
    "som_model_rent": float,
    "som_model_price": float,
}

CALC_COLUMNS_NAMES = {"price_per_square_meter": float, "age": int}

LOCATION_QUERY = """
{{
  {0} (filters: {1}) {{
    edges {{
      node {{
        immo_id,
        url,
        spider,
        is_active,
        uptime_date,
        title,
        square_meter,
        rooms,
        year_of_construction,
        price,
        rent_price,
        action,
        lat,
        lon,
        price_per_square_meter,
        rent_per_square_meter
      }}
    }}
  }}
}}""".strip()
