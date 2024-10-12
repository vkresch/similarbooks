import mongoengine as me
from mongoengine import Q
import argparse
import logging
import time
import tqdm
import requests
import datetime
from utils import model_dict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from app.similarbooks.config import Config
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)
from som.utils import get_top_bmus
from spiders.bookspider.bookspider.models import Book, Websom

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

# Connect to MongoDB using mongoengine
me.connect(db="similarbooks", host=Config.MONGODB_SETTINGS["host"])

# Max number of workers (adjust based on system capacity)
MAX_WORKERS = 5


def fetch_and_process_book(book):
    try:
        sha = update_model(book)
        logging.info(f"Processed book with SHA: {sha}")
    except Exception as e:
        logging.error(f"Error processing book: {e}")


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
        bmu_node = get_top_bmus(som, active_map, top_n=1)[0]

    bmu_update = {
        "bmu_col": int(bmu_node[0]),
        "bmu_row": int(bmu_node[1]),
    }

    # Update the document
    try:
        Book.objects(sha=sha).update_one(
            set__bmu_col=bmu_update["bmu_col"],
            set__bmu_row=bmu_update["bmu_row"],
        )
        Websom.objects(**bmu_update).update_one(
            add_to_set__matched_list=sha  # Add to list without duplication
        )
        logging.info(f"Updated new book {sha} to bmu node {bmu_update} in websom")
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

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(fetch_and_process_book, books)


if __name__ == "__main__":
    main()
