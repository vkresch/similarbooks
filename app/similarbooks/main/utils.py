import sys
import re
import flask
import datetime
import requests
import pickle
import json
from time import perf_counter
from urllib.parse import urlparse
from urllib.parse import parse_qs
import pandas as pd
import logging
import hashlib
from app.similarbooks.config import Config
from app.similarbooks.main.common import cache
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)

average_name_dict = {
    "kaufen": "avg_price_per_square_meter",
    "mieten": "avg_rent_per_square_meter",
}

TRACKING_ID = "findsimilarbooks-20"


def extract_and_add_params(url):
    if url is None:
        return
    parsed_url = urlparse(url)

    # Base part of the new URL
    base_url = None

    # Check if the path contains "/gp/product" or "/dp"
    # https://affiliate-program.amazon.com/help/node/topic/GP38PJ6EUR6PFBEC
    if "/gp/product/" in parsed_url.path:
        # Extract the product ID using split and indexing
        product_id = parsed_url.path.split("/gp/product/")[1].split("/")[0]
        base_url = f"http://{parsed_url.netloc}/gp/product/{product_id}/ref=nosim?tag=findsimilarbooks-20"
    elif "/dp/" in parsed_url.path:
        # Extract the product ID using split and indexing
        product_id = parsed_url.path.split("/dp/")[1].split("/")[0]
        base_url = f"http://{parsed_url.netloc}/dp/{product_id}/ref=nosim?tag=findsimilarbooks-20"

    return base_url


def get_action(path):
    action = None
    if "/kaufen/" in path:
        action = "kaufen"
    elif "/mieten/" in path:
        action = "mieten"
    return action


def get_type(path):
    type = None
    if "/wohnung/" in path:
        type = "all_appartments"
    elif "/haus/" in path:
        type = "all_houses"
    return type


def get_types(path):
    type = None
    if "/wohnung/" in path:
        type = "wohnungen"
    elif "/haus/" in path:
        type = "haeuser"
    return type


def get_param(params, key, type=str, default=None):
    param = params.get(key, default)
    if param:
        try:
            converted = type(param[0])
            return converted
        except Exception as e:
            logging.warning(e)
            return None
    return None


def get_bool(bool_string, default=None):
    string_bool_mapping = {"true": True, "false": False}
    return string_bool_mapping.get(bool_string, default)


def get_zipcodes(search):
    if search:
        response = requests.get(
            OPENPLZAPI_LOCALITIES,
            params={"name": f"^{search.strip().lower()}$"},
            headers={"accept": "text/json"},
        ).json()
        return [int(item["postalCode"]) for item in response]
    return None


def get_data(
    query_string,
    filter_string,
):
    CACHE_TIMEOUT = 15 * 60  # 15min
    hashed_query_string = hashlib.sha1(filter_string.encode("utf-8")).hexdigest()
    t1_start = perf_counter()

    query = query_string.format(
        filter_string,
    )

    logging.debug(f"Query:\n{query}")

    # Make use only of the page specific string to hash a key
    hashed_query = hashlib.sha1(query.encode("utf-8")).hexdigest()
    response = cache.get(hashed_query)
    logging.debug(f"hashed_query: {hashed_query}")
    if response is None:
        response = requests.post(
            url=GRAPHQL_ENDPOINT,
            json={"query": query},
            headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
        ).json()
        cache.set(hashed_query, response, timeout=CACHE_TIMEOUT)

    books = response["data"]["all_books"]["edges"]

    logging.debug(
        f"Queried {len(books)} books in {(perf_counter() - t1_start):.2f} seconds"
    )

    return books


def query_data(
    query_string,
    filter_dict,
):
    query = []
    for filter_key, filter_value in filter_dict.items():
        if filter_value is not None:
            if isinstance(filter_value, str):
                filter_value = filter_value.replace('"', "'")
                query.append(f'{filter_key}: "{filter_value}"')
            else:
                if isinstance(filter_value, bool):
                    filter_value = f"{filter_value}".lower()

                if isinstance(filter_value, list):
                    filter_value = json.dumps(filter_value)

                query.append(f"{filter_key}: {filter_value}")
    filter_string = "{" + ",".join(query) + "}"
    return get_data(
        query_string,
        filter_string,
    )


def load_file(path):
    with open(path, "rb") as file_model:
        obj = pickle.load(file_model)
    return obj


def subtract_from_now(time_string):
    # Regular expression pattern to extract numerical value and unit
    pattern = re.compile(r"(\d+)([smMyhdw])")

    # Match the pattern
    match = pattern.match(time_string)

    if not match:
        print("Invalid time string format:", time_string)
        return None

    # Extract numerical value and unit from the matched groups
    value = int(match.group(1))
    unit = match.group(2)

    # Define time delta based on the unit
    if unit == "s":
        delta = datetime.timedelta(seconds=value)
    elif unit == "M":
        delta = datetime.timedelta(minutes=value)
    elif unit == "h":
        delta = datetime.timedelta(hours=value)
    elif unit == "d":
        delta = datetime.timedelta(days=value)
    elif unit == "w":
        delta = datetime.timedelta(weeks=value)
    elif unit == "m":
        delta = datetime.timedelta(
            days=30 * value
        )  # Assuming a month is 30 days for simplicity
    elif unit == "y":
        delta = datetime.timedelta(
            days=365 * value
        )  # Assuming a year is 365 days for simplicity
    else:
        print("Invalid time unit!")
        return None

    # Subtract the calculated delta from the current datetime
    result = datetime.datetime.now() - delta
    return str(result.strftime("%Y-%m-%dT%H"))


def get_filter_dict(url):
    parsed_url = urlparse(url)
    action = get_action(url)

    parsed_params = parse_qs(parsed_url.query)
    ort = get_param(parsed_params, "ort", str, None)
    book_id = get_param(parsed_params, "book_id", str, None)
    bundesland = get_param(parsed_params, "bl", str, None)
    title = get_param(parsed_params, "title", str, None)
    is_active = get_param(parsed_params, "is_active", str, None)
    is_foreclosure = get_param(parsed_params, "is_foreclosure", str, None)
    is_erbbaurecht = get_param(parsed_params, "is_erbbaurecht", str, None)
    price_has_changed = get_param(parsed_params, "price_has_changed", str, None)
    price_has_increased = get_param(parsed_params, "price_has_increased", str, None)
    price_below_market_value = get_param(parsed_params, "pbmv", str, None)
    percentage_market_value_min = get_param(parsed_params, "permvmi", float, None)
    percentage_market_value_max = get_param(parsed_params, "permvma", float, None)
    area_min = get_param(parsed_params, "ami", int, None)
    area_max = get_param(parsed_params, "ama", int, None)
    price_min = get_param(parsed_params, "pmi", int, None)
    price_max = get_param(parsed_params, "pma", int, None)
    cashflow_min = get_param(parsed_params, "cmi", int, None)
    cashflow_max = get_param(parsed_params, "cma", int, None)
    roi_min = get_param(parsed_params, "roimi", float, None)
    roi_max = get_param(parsed_params, "roima", float, None)
    cold_rent_min = get_param(parsed_params, "crmi", int, None)
    cold_rent_max = get_param(parsed_params, "crma", int, None)
    price_per_square_meter_min = get_param(parsed_params, "psqmi", int, None)
    price_per_square_meter_max = get_param(parsed_params, "psqma", int, None)
    rent_per_square_meter_min = get_param(parsed_params, "rsqmi", int, None)
    rent_per_square_meter_max = get_param(parsed_params, "rsqma", int, None)
    year_of_construction_min = get_param(parsed_params, "ymi", int, None)
    year_of_construction_min = (
        year_of_construction_min
        if year_of_construction_min and 0 <= year_of_construction_min <= 9999
        else None
    )
    year_of_construction_max = get_param(parsed_params, "yma", int, None)
    year_of_construction_max = (
        year_of_construction_max
        if year_of_construction_max and 0 <= year_of_construction_max <= 9999
        else None
    )
    uptime_min = get_param(parsed_params, "upmi", str, None)
    datemi = get_param(parsed_params, "datemi", str, None)
    spider = get_param(parsed_params, "spider", str, None)

    filter_dict = {
        "book_id_in": book_id,
        "is_active": get_bool(is_active) if is_active is not None else True,
        "action": action,
        "zipcode_in": get_zipcodes(ort),
        "location": bundesland,
        "title_contains": title,
        "square_meter_gt": area_min,
        "square_meter_lt": area_max,
        "price_lt": price_max,
        "price_gt": price_min,
        "cashflow_lt": cashflow_max,
        "cashflow_gt": cashflow_min,
        "roi_lt": roi_max,
        "roi_gt": roi_min,
        "price_per_square_meter_lt": price_per_square_meter_max,
        "price_per_square_meter_gt": price_per_square_meter_min,
        "rent_price_lt": cold_rent_max,
        "rent_price_gt": cold_rent_min,
        "rent_per_square_meter_lt": rent_per_square_meter_max,
        "rent_per_square_meter_gt": rent_per_square_meter_min,
        "year_of_construction_lt": (
            datetime.datetime(year_of_construction_max, 1, 1).strftime(
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            if year_of_construction_max
            else None
        ),
        "year_of_construction_gt": (
            datetime.datetime(year_of_construction_min, 1, 1).strftime(
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            if year_of_construction_min
            else None
        ),
        "uptime_date_gt": subtract_from_now(uptime_min) if uptime_min else None,
        "date_gt": (subtract_from_now(datemi) if datemi else None),
        "price_has_changed": get_bool(price_has_changed),
        "price_has_increased": get_bool(price_has_increased),
        "price_below_market_value": get_bool(price_below_market_value),
        "som_model_percentage_gt": percentage_market_value_min,
        "som_model_percentage_lt": percentage_market_value_max,
        "spider": spider,
        "is_foreclosure": get_bool(is_foreclosure),
        "is_erbbaurecht": get_bool(is_erbbaurecht),
    }
    logging.debug(filter_dict)
    return filter_dict


def check_similarity(node, clustered_real_estates):
    if node.get("year_of_construction") is None:
        return (
            clustered_real_estates["square_meter"] == node["square_meter"]
            and clustered_real_estates["rooms"] == node["rooms"]
            and clustered_real_estates["action"] == node["action"]
        )
    return (
        clustered_real_estates["square_meter"] == node["square_meter"]
        and clustered_real_estates["rooms"] == node["rooms"]
        and clustered_real_estates["action"] == node["action"]
        and clustered_real_estates["year_of_construction"][:4]
        == node["year_of_construction"][:4]
    )
