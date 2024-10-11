import pymongo
import argparse
import logging
import time
import tqdm
import requests
import datetime
from utils import model_dict
import numpy as np
from app.similarbooks.config import Config
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)
from som.utils import get_top_bmus

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Connect to the MongoDB server
CLIENT = pymongo.MongoClient(Config.MONGODB_SETTINGS["host"])

# Get the appartment database and the appartment collection
DB = CLIENT["similarbooks"]

LDA_WEBSOM_COLLECTION = DB["lda_websom"]
BOOK_COLLECTION = DB["book"]


def update_model(sha, bmu_update):
    # Update the document
    try:
        BOOK_COLLECTION.update_one({"sha": sha}, {"$set": bmu_update})
        logging.info(f"Update book {sha} with {bmu_update}")
    except Exception as e:
        logging.error(e)
        return "xxxxx"

    return sha


def main():

    for row in range(model_dict["lda_websom"].codebook.shape[0]):
        for col in range(model_dict["lda_websom"].codebook.shape[1]):
            bmu = {
                "bmu_col": col,
                "bmu_row": row,
            }
            matched_documents = LDA_WEBSOM_COLLECTION.find(bmu)
            for document in matched_documents:
                for sha in document.get("matched_list"):
                    update_model(sha, bmu)


if __name__ == "__main__":
    main()
