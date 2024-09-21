import argparse
import logging
from tqdm.auto import trange
import requests
import datetime
import somoclu
import pandas as pd
import numpy as np
import pickle
import json
from time import perf_counter
from pathlib import Path
from Scaler import Scaler
from concurrent.futures import ProcessPoolExecutor, as_completed
from app.similarbooks.main.constants import GRAPHQL_ENDPOINT, MODEL_NAMES, MODEL_QUERIES
from app.similarbooks.config import Config


def command_line_arguments():
    """Define and handle command line interface"""
    parser = argparse.ArgumentParser(description="Train som model", prog="trainsom")
    parser.add_argument(
        "--rows",
        "-r",
        help="Row count of the SOM.",
        default=250,
        type=int,
    )
    parser.add_argument(
        "--cols",
        "-c",
        help="Column count of the SOM.",
        default=250,
        type=int,
    )
    parser.add_argument(
        "--epochs",
        "-e",
        help="Number of epochs to train the SOM.",
        default=250,
        type=int,
    )
    parser.add_argument(
        "--type",
        "-t",
        help="Type of real estate to crawl.",
        choices=["all_appartments", "all_houses"],
        default="all_appartments",
        type=str,
    )
    return parser.parse_args()


args = command_line_arguments()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent

FILTER_QUERY = """
{{
  {0} (filters: {1}) {{
    edges {{
      node {{
        immo_id,
        square_meter,
        rooms,
        year_of_construction,
        lat,
        lon
      }}
    }}
  }}
}}""".strip()

COLUMN_NAMES = {
    "square_meter": float,
    "rooms": float,
    "year_of_construction": int,
    "immo_id": str,
    "lat": float,
    "lon": float,
}

ATTRIBUTE_QUERY = """
{{
  {0} (filters: {1}) {{
    edges {{
      node {{
        immo_id,
        rent_price,
        price,
        square_meter,
        location,
        maintenance_price,
        year_of_construction
      }}
    }}
  }}
}}""".strip()

ATTRIBUTE_COLUMN_NAMES = {
    "immo_id": str,
    "price": float,
    "rent_price": float,
    "square_meter": float,
    "year_of_construction": int,
    "location": str,
    "maintenance_price": float,
}

# Cashflow parameters
REAL_ESTATE_TAX_RATIO_DICT = {
    "bl-schleswig-holstein": 0.065,
    "bl-mecklenburg-vorpommern": 0.06,
    "hamburg": 0.045,
    "bremen": 0.05,
    "bl-nordrhein-westfalen": 0.065,
    "bl-niedersachsen": 0.05,
    "bl-sachsen-anhalt": 0.05,
    "bl-sachsen": 0.035,
    "bl-thueringen": 0.065,
    "bl-hessen": 0.06,
    "bl-rheinland-pfalz": 0.05,
    "bl-brandenburg": 0.065,
    "bl-saarland": 0.065,
    "berlin": 0.06,
    "bl-baden-wuerttemberg": 0.05,
    "bl-bayern": 0.035,
}

# Cost specifics
AGENT_RATIO = 0.0357
NOTAR_RATIO = 0.015
GRUNDBUCH_RATIO = 0.005
EQUITY_CAPITAL = 25_000
MAINTENANCE_PRICE_PER_SQUARE_METER = 3.0
MAINTENANCE_PAY_RATIO_OWNER = 0.4
TAX_RATE = 0.4

# Mortgage specifics
TILGUNGS_RATIO = 0.02
EFFEKTIV_ZINS = 0.0353
ANNUITY_RATE = EFFEKTIV_ZINS + TILGUNGS_RATIO


def view_matrix(som, matrix):
    som._view_matrix(
        matrix,
        figsize=None,
        colormap=None,
        colorbar=None,
        bestmatches=None,
        bestmatchcolors=None,
        labels=None,
        zoom=None,
        filename=None,
    )


def process_year_of_construction(df):
    df.loc[
        df["year_of_construction"].str.contains("2022", na=False),
        "year_of_construction",
    ] = "2022"
    df.loc[
        df["year_of_construction"].str.contains("2023", na=False),
        "year_of_construction",
    ] = "2023"
    df.loc[
        df["year_of_construction"].str.contains("22/23", na=False),
        "year_of_construction",
    ] = "2022"
    df.loc[
        df["year_of_construction"].str.contains("23/24", na=False),
        "year_of_construction",
    ] = "2022"

    df["year_of_construction"] = pd.to_numeric(
        df.year_of_construction.str.extract(r"(\d+)", expand=False)
    )
    return df


def process_age(df):
    # Custom transformations
    # df = process_year_of_construction(df)
    df.dropna(subset=["year_of_construction"], inplace=True)
    df.loc[:, "year_of_construction"] = (
        df.loc[:, "year_of_construction"].str[:4].astype(int)
    )
    df.loc[:, "age"] = datetime.date.today().year - df.loc[:, "year_of_construction"]
    # df["age"].replace(to_replace=0, value=df["age"].mean(), inplace=True)
    # df["age"].fillna(round(df["age"].mean()), inplace=True)
    # df["age"] = df["age"].clip(lower=0, upper=500)
    return df


def process_energy_consumption(df):
    df["energy_consumption"] = pd.to_numeric(
        df.energy_consumption.str.extract("(\d+)", expand=False)
    )
    df["energy_consumption"].fillna(
        round(df["energy_consumption"].mean(), 2), inplace=True
    )
    return df


def process_floor_number(df):
    df["floor_number"] = df["floor_number"].str.replace(r" \(Dachgeschoss\)", "")
    df["floor_number"] = df["floor_number"].str.replace(r" \(Erdgeschoss\)", "")
    df["floor_number"] = df["floor_number"].str.replace(r" \(Souterrain\)", "")
    df["floor_number"] = df.floor_number.apply(
        lambda s: "-" + s if (s is not None) and ("Untergeschoss" in s) else s
    )
    df.loc[
        df["floor_number"].str.contains(r"Erdgeschoss", case=False, na=False),
        "floor_number",
    ] = 0
    df.loc[
        df["floor_number"].str.contains(r"Souterrain", case=False, na=False),
        "floor_number",
    ] = 0
    df.loc[
        df["floor_number"].str.contains(r"Dachgeschoss", case=False, na=False),
        "floor_number",
    ] = 5
    df["floor_number"] = df["floor_number"].str.replace(r"\. Geschoss", "")
    df["floor_number"] = df["floor_number"].str.replace(r"\. Untergeschoss", "")

    df["floor_number"] = pd.to_numeric(
        df.floor_number.str.extract("(\d+)", expand=False)
    )
    # df["floor_number"].fillna(round(df["floor_number"].mean()), inplace=True)
    df["floor_number"] = df["floor_number"].clip(lower=0, upper=10)
    return df


def remove_year_of_construction(df):
    del df["year_of_construction"]
    df = df[df["age"] >= -20]
    df = df[df["age"] < 2000]
    return df


def query_data(model_name):
    query_string = MODEL_QUERIES.get(model_name)
    logging.info("Getting data ...")
    query = FILTER_QUERY.format(args.type, query_string)
    logging.info(f"Query: {query}")
    response = requests.post(
        url=GRAPHQL_ENDPOINT,
        json={"query": query},
        headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
    ).json()
    appartments = response["data"][args.type]["edges"]
    if len(appartments) == 0:
        raise Exception(f"No real estate found for the following query: {query}")
    return appartments


def get_data(appartments, column_list):
    # TODO: Optimize this for loop
    plot_data = {column_name: [] for column_name in COLUMN_NAMES}
    for appartment in appartments:
        for attribute, attribute_type in COLUMN_NAMES.items():
            plot_data[attribute].append(appartment["node"][attribute])
    df = pd.DataFrame(plot_data)
    df.drop(df[df.square_meter == 0].index, inplace=True)

    # Filter columns
    df = df[column_list]

    # Prepare age
    if "year_of_construction" in column_list:
        df = process_age(df)
        df = remove_year_of_construction(df)

    # Prepare floor number
    # df = process_floor_number(df)

    # Process energy consumption
    # df = process_energy_consumption(df)

    df.set_index("immo_id", inplace=True)
    return df


def main():
    # BUNDESLAENDER_LIST = list(REAL_ESTATE_TAX_RATIO_DICT)
    # BUNDESLAENDER_LIST.append("all")
    for model_name, column_list in MODEL_NAMES.items():
        appartments = query_data(model_name)
        data = get_data(appartments, column_list)
        logging.info(f"Data shape: {data.shape}")
        # data.to_csv("/home/vkreschenski/Documents/Privat/Freelancer/similarbooks/df.csv")
        som = somoclu.Somoclu(
            args.cols,
            args.rows,
            compactsupport=True,
            maptype="toroid",
            verbose=2,
            initialization="pca",
        )
        data.dropna(inplace=True)
        logging.info(f"Dropped data shape: {data.shape}")
        # data.to_csv("/home/vkreschenski/projects/similarbooks/som/df.csv")
        scaler = Scaler()
        scaled_data = scaler.scale(data)
        with open(
            PARENT_DIR / Path(f"models/{args.type}_{model_name}_scaler.pkl"), "wb"
        ) as file_model:
            scaler.name = f"{args.type}_{model_name}_scaler"
            pickle.dump(scaler, file_model, pickle.HIGHEST_PROTOCOL)

        # Start the stopwatch / counter
        t1_start = perf_counter()
        logging.info(f"[{args.type}] Training start: {datetime.datetime.now()}")
        som.train(
            data=scaled_data.to_numpy(dtype="float32"),
            epochs=args.epochs,
            radiuscooling="exponential",
            scalecooling="exponential",
        )
        logging.info(f"Training finished: {datetime.datetime.now()}")

        # Stop the stopwatch / counter
        t1_stop = perf_counter()

        delta_seconds = t1_stop - t1_start
        logging.info(f"Elapsed time for training in seconds: {delta_seconds}")
        logging.info(f"Elapsed time for training in minutes: {delta_seconds / 60.0}")
        logging.info(f"Elapsed time for training in hours: {delta_seconds / 3600.0}")

        som.labels = scaled_data.index

        with open(
            PARENT_DIR / Path(f"models/{args.type}_{model_name}_model.pkl"), "wb"
        ) as file_model:
            som.name = f"{args.type}_{model_name}_model"
            pickle.dump(som, file_model, pickle.HIGHEST_PROTOCOL)

        # view_matrix(som, som.cashflow)
        # view_matrix(som, som.price_matrix)
        # view_matrix(som, som.total_price)
        # view_matrix(som, som.rent_price_matrix)
        # view_matrix(som, som.node_count)
        # som.view_umatrix()
        # som.view_component_planes()


if __name__ == "__main__":
    main()
