import pymongo
import argparse
import logging
import time
import tqdm
import requests
import datetime
from utils import model_dict
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

ATTRIBUTE_QUERY = """
{{
  all_books (filters: {0}) {{
    edges {{
      node {{
        sha,
        title,
        summary,
      }}
    }}
  }}
}}""".strip()

# Connect to the MongoDB server
CLIENT = pymongo.MongoClient(Config.MONGODB_SETTINGS["host"])

# Get the appartment database and the appartment collection
DB = CLIENT["similarbooks"]

LDA_WEBSOM_COLLECTION = DB["lda_websom"]
BOOK_COLLECTION = DB["book"]


def update_model(book):
    data = book["node"]
    sha = data["sha"]

    som = model_dict["lda_websom"]
    bmu_node = som.labels.get(sha)

    if bmu_node is None:
        tasks_vectorized = model_dict["vectorizer"].transform(
            [(data.get("title") or "") + " " + (data.get("summary") or "")]
        )
        tasks_topic_dist = model_dict["lda"].transform(tasks_vectorized)[0]
        active_map = som.get_surface_state(data=np.array([tasks_topic_dist]))
        bmu_node = get_top_bmus(som, active_map, top_n=1)

    bmu_update = {
        "bmu_col": int(bmu_node[0]),
        "bmu_row": int(bmu_node[1]),
    }

    matched_documents = LDA_WEBSOM_COLLECTION.find(bmu_update)
    matched_list = []
    for doc in matched_documents:
        matched_list.extend(doc["matched_list"])

    # Update the document
    try:
        BOOK_COLLECTION.update_one({"sha": sha}, {"$set": bmu_update})
        logging.info(f"Update book {sha} with {bmu_update}")
        if sha not in matched_list:
            matched_list.append(sha)
            LDA_WEBSOM_COLLECTION.update_one(
                bmu_update, {"$set": {"matched_list": matched_list}}
            )
            logging.info(f"Appended new book {sha} to bmu node {bmu_update} in websom")
    except Exception as e:
        logging.error(e)
        return "xxxxx"

    return sha


def main():
    while True:
        logging.info("Getting data ...")
        query_string = "{language: 'English', summary_length_gte: 400, bmu_col_exists: false, bmu_row_exists: false}"
        query = ATTRIBUTE_QUERY.format(
            query_string,
        ).replace("'", '"')
        logging.info(f"Query:\n{query}")
        response = requests.post(
            url=GRAPHQL_ENDPOINT,
            json={"query": query},
        ).json()
        books = response["data"]["all_books"]["edges"]
        logging.info(f"Got data with length {len(books)}")
        pbooks = tqdm.tqdm(books)
        for book in pbooks:
            sha = update_model(book)
            pbooks.set_description(f"sha {sha}")
        time.sleep(1)


if __name__ == "__main__":
    main()
