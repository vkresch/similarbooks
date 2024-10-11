import pymongo
import argparse
import logging
import tqdm
import numpy as np
import pandas as pd
import requests
import datetime
from utils import model_dict
from app.similarbooks.config import Config
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Connect to the MongoDB server
CLIENT = pymongo.MongoClient(Config.MONGODB_SETTINGS["host"])

# Get the appartment database and the appartment collection
DB = CLIENT["similarbooks"]


def process_model(som):
    logging.info(f"Updating database for {som.name} ...")

    # Get or create the collection for the current som.name
    collection = DB[som.name]

    # Create a compound index
    collection.create_index(
        [("bmu_col", pymongo.ASCENDING), ("bmu_row", pymongo.ASCENDING)], unique=True
    )

    for row in tqdm.trange(som.codebook.shape[0]):
        for col in range(som.codebook.shape[1]):
            bmu_nodes = np.array([[[col, row]]])
            matched_indices = np.any(
                np.all(bmu_nodes == som.bmus[:, None, :], axis=2), axis=1
            )
            matched_list = list(pd.Series(som.labels.keys())[matched_indices])

            # Prepare the document to insert
            document = {"matched_list": matched_list}

            # Upsert the document into the collection
            collection.update_one(
                {"bmu_col": col, "bmu_row": row}, {"$set": document}, upsert=True
            )


if __name__ == "__main__":
    process_model(model_dict["lda_websom"])
