import sys
import re
import flask
import datetime
import requests
import pickle
from time import perf_counter
from urllib.parse import urlparse
from urllib.parse import parse_qs
import pandas as pd
from som.utils import get_matched_immo_ids, get_clustered_real_estate
import logging
import hashlib
from app.similarbooks.config import Config
from app.similarbooks.main.common import cache
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
    KAUFEN_QUERY,
    CACHED_KAUFEN_QUERY,
    MIETEN_QUERY,
    CACHED_MIETEN_QUERY,
    LOCATION_QUERY,
    BASIC_QUERY,
    OPENPLZAPI_LOCALITIES,
    DEBUG,
    DEFAULT_INTEREST,
    DEFAULT_REPAYMENT,
    DEFAULT_EQUITY,
)

average_name_dict = {
    "kaufen": "avg_price_per_square_meter",
    "mieten": "avg_rent_per_square_meter",
}


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


def get_cached_query(
    query_string,
    page,
    order_by,
    action,
    estate_type,
    equity_percentage,
    interest,
    repayment,
):
    if action == "kaufen":
        query = CACHED_KAUFEN_QUERY.format(
            estate_type,
            order_by,
            page,
            query_string,
            equity_percentage,
            interest,
            repayment,
        )
    elif action == "mieten":
        query = CACHED_MIETEN_QUERY.format(
            estate_type,
            order_by,
            page,
            query_string,
        )
    else:
        raise Exception(f"action: {action} does not exist!")
    return query.replace("'", '"')


def get_query(
    query_string,
    page,
    order_by,
    action,
    estate_type,
    equity_percentage,
    interest,
    repayment,
    count_estate=None,
    avg_estate=None,
):
    if action == "kaufen":
        query = KAUFEN_QUERY.format(
            estate_type,
            order_by,
            page,
            query_string,
            count_estate,
            avg_estate,
            equity_percentage,
            interest,
            repayment,
        )
    elif action == "mieten":
        query = MIETEN_QUERY.format(
            estate_type,
            order_by,
            page,
            query_string,
            count_estate,
            avg_estate,
        )
    else:
        raise Exception(f"action: {action} does not exist!")

    return query.replace("'", '"')


def get_data(
    query_string,
    page,
    order_by,
    action,
    estate_type,
    equity_percentage,
    interest,
    repayment,
):
    CACHE_TIMEOUT = 15 * 60  # 15min
    hashed_query_string = hashlib.sha1(query_string.encode("utf-8")).hexdigest()
    if estate_type is None:
        logging.warning("No estate type selected!")
        return {}, 0, 0

    count_estate = (
        "total_appartments_count"
        if estate_type == "all_appartments"
        else "total_houses_count"
    )
    count = cache.get(f"{hashed_query_string}{count_estate}")
    avg_estate = "avg_appartments" if estate_type == "all_appartments" else "avg_houses"
    avg_price_per_square_meter = cache.get(f"{hashed_query_string}{avg_estate}")

    t1_start = perf_counter()
    cashed_query = get_cached_query(
        query_string,
        page,
        order_by,
        action,
        estate_type,
        equity_percentage,
        interest,
        repayment,
    )

    query = get_query(
        query_string,
        page,
        order_by,
        action,
        estate_type,
        equity_percentage,
        interest,
        repayment,
        count_estate,
        avg_estate,
    )

    if count is not None or avg_price_per_square_meter is not None:
        query = cashed_query

    logging.debug(f"Query:\n{query}")

    # Make use only of the page specific string to hash a key
    hashed_query = hashlib.sha1(cashed_query.encode("utf-8")).hexdigest()
    response = cache.get(hashed_query)
    logging.debug(f"hashed_query: {hashed_query}")
    if response is None:
        response = requests.post(
            url=GRAPHQL_ENDPOINT,
            json={"query": query},
            headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
        ).json()
        cache.set(hashed_query, response, timeout=CACHE_TIMEOUT)
    real_estate = response["data"][estate_type]["edges"]

    if count is None:
        count = response["data"][count_estate]
        cache.set(f"{hashed_query_string}{count_estate}", count, timeout=CACHE_TIMEOUT)

    # NOTE: Make sure the average is calculatable
    if avg_price_per_square_meter is None:
        results = response["data"][avg_estate]["edges"]
        if len(results) > 0:
            avg_price_per_square_meter = results[0]["node"][average_name_dict[action]]
            cache.set(
                f"{hashed_query_string}{avg_estate}",
                avg_price_per_square_meter,
                timeout=CACHE_TIMEOUT,
            )
    logging.debug(
        f"Queried {len(real_estate)} real estates in {(perf_counter() - t1_start):.2f} seconds from total real estates of {count}"
    )

    return real_estate, count, avg_price_per_square_meter


def query_data(
    filter_dict,
    page,
    order_by,
    estate_type,
    equity_percentage,
    interest,
    repayment,
):
    query = []
    for filter_key, filter_value in filter_dict.items():
        if filter_value is not None:
            if isinstance(filter_value, str):
                query.append(f"{filter_key}: '{filter_value}'")
            else:
                if isinstance(filter_value, bool):
                    filter_value = f"{filter_value}".lower()
                query.append(f"{filter_key}: {filter_value}")
    query_string = "{" + ",".join(query) + "}"
    return get_data(
        query_string,
        page,
        order_by,
        filter_dict["action"],
        estate_type,
        equity_percentage,
        interest,
        repayment,
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
    immo_id = get_param(parsed_params, "immo_id", str, None)
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
        "immo_id_in": immo_id,
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


def get_detailed_data(immo_id, typ, cashflow_parameter):
    CACHE_TIMEOUT = 60 * 60  # 1h
    query_string = "{{immo_id: '{0}'}}".format(immo_id)
    query = BASIC_QUERY.format(
        typ,
        query_string,
        cashflow_parameter.get("equity_percentage"),
        cashflow_parameter.get("interest"),
        cashflow_parameter.get("repayment"),
    ).replace("'", '"')
    logging.debug(f"Query:\n{query}")
    response = cache.get(hashlib.sha1(query.encode("utf-8")).hexdigest())
    if response is None:
        response = requests.post(
            url=GRAPHQL_ENDPOINT,
            json={"query": query},
            headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
        ).json()
        cache.set(
            hashlib.sha1(query.encode("utf-8")).hexdigest(),
            response,
            timeout=CACHE_TIMEOUT,
        )
    real_estate = response["data"][typ]["edges"]
    if len(real_estate) == 0:
        logging.warning(
            f"No real estate found for immo_id: {immo_id} with lat and lon!"
        )
        return None
    node = real_estate[0]["node"]
    immo_ids = []
    if (
        node["lat"] is not None
        and node["lon"] is not None
        and node["square_meter"] is not None
    ):
        _, immo_ids = get_matched_immo_ids(
            typ, node, node.get("immo_id"), update_som=True
        )
    # NOTE: display foreclosure and erbbaurecht here too
    cluster_query = LOCATION_QUERY.format(
        typ,
        "{{immo_id_in: {0}, lat_exists: true, lon_exists: true}}".format(immo_ids),
    ).replace("'", '"')
    cluster_response = cache.get(
        hashlib.sha1(cluster_query.encode("utf-8")).hexdigest()
    )
    if cluster_response is None:
        cluster_response = requests.post(
            url=GRAPHQL_ENDPOINT,
            json={
                "query": cluster_query,
            },
            headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
        ).json()
        cache.set(
            hashlib.sha1(cluster_query.encode("utf-8")).hexdigest(),
            cluster_response,
            timeout=CACHE_TIMEOUT,
        )
    real_estates = cluster_response["data"][typ]["edges"]
    clustered_real_estates = get_clustered_real_estate(real_estates)
    similar_real_estates = {
        cre["immo_id"]: {
            "spider": cre["spider"],
            "url": cre["url"],
            "uptime_date": cre["uptime_date"],
            "price": cre["price"],
            "rent_price": cre["rent_price"],
        }
        for cre in clustered_real_estates
        if immo_id != cre["immo_id"] and check_similarity(node, cre)
    }
    node["similar_real_estates"] = similar_real_estates
    node["clustered_real_estates"] = clustered_real_estates
    return node


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


def get_data_from_url(
    url,
    sort="-uptime_date",
    page=1,
    equity_percentage=DEFAULT_EQUITY,
    interest=DEFAULT_INTEREST,
    repayment=DEFAULT_REPAYMENT,
):
    return query_data(
        filter_dict=get_filter_dict(url),
        page=page,
        order_by=sort,
        estate_type=get_type(url),
        equity_percentage=equity_percentage,
        interest=interest,
        repayment=repayment,
    )
