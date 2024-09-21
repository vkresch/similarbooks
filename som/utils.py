import sys
import pickle
import pymongo
import datetime
import requests
import pandas as pd
import numpy as np
from pathlib import Path
import som.Scaler as Scaler
from geopy.geocoders import Nominatim
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
    LOCATION_QUERY,
    MIN_BMU_PROPERTY_COUNT,
)
from app.similarbooks.config import Config

sys.modules["Scaler"] = Scaler

PARENT_DIR = Path(__file__).resolve().parent

# Connect to the MongoDB server
CLIENT = pymongo.MongoClient(Config.MONGODB_SETTINGS["host"])
DB = CLIENT["similarbooks"]


def load_file(path):
    with open(path, "rb") as file_model:
        obj = pickle.load(file_model)
    return obj


model_dict = {}


def get_clustered_real_estate(real_estates):
    return [
        {
            "immo_id": re["node"]["immo_id"],
            "is_active": re["node"]["is_active"],
            "lat": re["node"]["lat"],
            "lon": re["node"]["lon"],
            "title": re["node"]["title"].replace("\n", " ").replace("\r", ""),
            "square_meter": re["node"]["square_meter"],
            "rooms": re["node"]["rooms"],
            "year_of_construction": (
                re["node"]["year_of_construction"][:18]
                if re["node"]["year_of_construction"]
                else None
            ),
            "price": re["node"]["price"],
            "price_per_square_meter": re["node"]["price_per_square_meter"],
            "rent_price": re["node"]["rent_price"],
            "rent_per_square_meter": re["node"]["rent_per_square_meter"],
            "action": re["node"]["action"],
            "uptime_date": re["node"]["uptime_date"][:18],
            "spider": re["node"]["spider"],
            "url": re["node"]["url"],
        }
        for re in real_estates
    ]


def get_price_per_square_meter(typ, data, immo_id, update_som=False):
    if data["lat"] is None or data["lon"] is None or data["square_meter"] is None:
        return None, None, []
    som, immo_ids = get_matched_immo_ids(typ, data, immo_id, update_som)
    cluster_query = LOCATION_QUERY.format(
        typ,
        "{{immo_id_in: {0}, lat_exists: true, , lon_exists: true, is_foreclosure: false, is_erbbaurecht: false}}".format(
            immo_ids
        ),
    ).replace("'", '"')
    cluster_response = requests.post(
        url=GRAPHQL_ENDPOINT,
        json={
            "query": cluster_query,
        },
        headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
    ).json()
    if cluster_response.get("data") is None:
        return None, None, []
    real_estates = cluster_response["data"][typ]["edges"]
    clustered_real_estates = get_clustered_real_estate(real_estates)
    if len(clustered_real_estates) > 0:
        # TODO: Add here the similarity check to avoid average calculation error
        df = pd.DataFrame.from_dict(clustered_real_estates).drop_duplicates(
            subset=[
                "square_meter",
                "year_of_construction",
                "rooms",
                "price",
                "rent_price",
                "action",
            ]
        )
        filtered_rent_df = df[(df["rent_price"] > 100) & (df["rent_price"] < 15_000)]
        rent_price_per_square_meter = filtered_rent_df["rent_per_square_meter"].mean()

        filtered_price_df = df[(df["price"] > 15_000)]
        price_per_square_meter = filtered_price_df["price_per_square_meter"].mean()
        return (
            rent_price_per_square_meter,
            price_per_square_meter,
            clustered_real_estates,
        )
    return None, None, clustered_real_estates


geolocator = Nominatim(user_agent="immolocation")


def get_coordinates(street, zipcode):
    zipcode_str = f"{zipcode}"
    if len(zipcode_str) == 4:
        zipcode_str = f"0{zipcode_str}"
    location = geolocator.geocode(
        {"postalcode": zipcode_str, "street": street, "country": "Germany"}
    )
    if location is None:
        location = geolocator.geocode({"postalcode": zipcode_str, "country": "Germany"})

    if location is None:
        return {"lat": None, "lon": None}

    return {"lat": location.latitude, "lon": location.longitude}


def get_top_bmus(som, activation_map, top_n):
    """Returns the top n matching units.

    :param activation_map: Activation map computed with som.get_surface_state()
    :type activation_map: 2D numpy.array

    :returns: The bmus indexes and the second bmus indexes corresponding to
              this activation map (same as som.bmus for the training samples).
    :rtype: tuple of 2D numpy.array
    """

    # Normal BMU finding
    if top_n == 1:
        return som.get_bmus(activation_map)

    n_samples = activation_map.shape[0]
    top_bmus_combined = np.empty((n_samples, top_n, 2), dtype=int)
    for n in range(top_n):
        # Get the BMU indices
        bmu_indices = activation_map.argmin(axis=1)
        Y, X = np.unravel_index(bmu_indices, (som._n_rows, som._n_columns))
        top_bmus_combined[:, n, :] = np.vstack((X, Y)).T

        # Mask the BMU values
        activation_map[np.arange(n_samples), bmu_indices] = np.inf

    return top_bmus_combined[0]


def update(som, immo_id, bmu):
    collection = DB[som.name]
    matched_list = collection.find_one({"bmu_id": bmu}).get("matched_list")
    if immo_id not in matched_list:
        matched_list.append(immo_id)

        # Prepare the document to insert
        document = {"bmu_id": bmu, "matched_list": matched_list}

        # Upsert the document into the collection
        collection.update_one({"bmu_id": bmu}, {"$set": document}, upsert=True)


def get_matched_immo_ids(typ, data, immo_id=None, update_som=False):
    top_n = 1
    merged_matched_list = []
    while len(merged_matched_list) < MIN_BMU_PROPERTY_COUNT:
        som, bmu_nodes = get_bmus(typ, data, top_n)
        bmu_list = bmu_nodes.tolist()
        collection = DB[som.name]
        matched_documents = collection.find({"bmu_id": {"$in": bmu_list}})
        for document in matched_documents:
            matched_list = document["matched_list"]
            merged_matched_list.extend(matched_list)
        top_n += 1

    if update_som:
        update(som, immo_id, [bmu_list[0]])
    if immo_id in merged_matched_list:
        merged_matched_list.remove(immo_id)
    return som, merged_matched_list


def get_bmus(typ, data, top_n=1):
    model = "lat_lon_sq_bj_ro"
    flat_dict = {
        "immo_id": ["xxx"],
        "lat": [data["lat"]],
        "lon": [data["lon"]],
        "square_meter": [data["square_meter"]],
    }
    year_of_construction = data.get("year_of_construction")
    rooms = data.get("rooms")

    if year_of_construction and rooms:
        flat_dict["rooms"] = [data["rooms"]]
        flat_dict["age"] = [
            datetime.date.today().year - int(data["year_of_construction"][:4])
        ]

    if rooms and year_of_construction is None:
        model = "lat_lon_sq_ro"
        flat_dict["rooms"] = [data["rooms"]]

    if year_of_construction and rooms is None:
        model = "lat_lon_sq_bj"
        flat_dict["age"] = [
            datetime.date.today().year - int(data["year_of_construction"][:4])
        ]

    if year_of_construction is None and rooms is None:
        model = "lat_lon_sq"
    som = model_dict[typ][model]["som"]

    # Proceed with model calculation
    df = pd.DataFrame.from_dict(flat_dict)
    df.set_index("immo_id", inplace=True)
    scaled_df = model_dict[typ][model]["scaler"].transform(df)
    active_map = som.get_surface_state(data=scaled_df.to_numpy())
    bmu_nodes = get_top_bmus(som, active_map, top_n=top_n)
    return som, bmu_nodes
