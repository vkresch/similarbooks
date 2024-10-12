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
from som.utils import get_surface_state
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

BATCH_SIZE = 50  # Adjust batch size as per system's capacity


def vectorize_books(books):
    # Prepare texts for vectorization
    texts = [
        (book["node"]["title"] or "") + " " + (book["node"]["summary"] or "")
        for book in books
    ]
    # Batch vectorization
    logging.info("Vectorizing books in batch ...")
    return model_dict["vectorizer"].transform(texts)


def lda_transform_batch(tasks_vectorized):
    # Batch LDA transformation
    logging.info("Performing LDA transformation in batch ...")
    return model_dict["lda"].transform(tasks_vectorized)


def som_mapping_batch(tasks_topic_dist_batch):
    # Batch SOM mapping
    logging.info("Mapping onto the SOM in batch ...")
    return get_surface_state(data=tasks_topic_dist_batch)


def process_batch(books):
    # Step 1: Batch vectorization
    tasks_vectorized = vectorize_books(books)

    # Step 2: Batch LDA transformation
    tasks_topic_dist_batch = lda_transform_batch(tasks_vectorized)

    # Step 3: Batch SOM Mapping (parallelized if possible)
    activation_maps = som_mapping_batch(tasks_topic_dist_batch)

    # Step 4: Get BMUs
    bmu_nodes = model_dict["lda_websom"].get_bmus(activation_maps)

    # Step 5: Update database in batch
    for i, book in enumerate(books):
        sha = book["node"]["sha"]
        bmu_node = bmu_nodes[i]

        bmu_update = {
            "bmu_col": int(bmu_node[0]),
            "bmu_row": int(bmu_node[1]),
        }

        # Update the database
        Book.objects(sha=sha).update_one(
            set__bmu_col=bmu_update["bmu_col"],
            set__bmu_row=bmu_update["bmu_row"],
        )
        Websom.objects(**bmu_update).update_one(
            add_to_set__matched_list=sha  # Add to list without duplication
        )
        logging.info(f"Updated book {sha} to bmu node {bmu_update} in Websom")


def fetch_data():
    logging.info("Getting data ...")
    query_string = "{language: 'English', summary_length_gte: 400, bmu_col_exists: false, bmu_row_exists: false}"
    query = ATTRIBUTE_QUERY.format(query_string).replace("'", '"')
    logging.info(f"Query:\n{query}")
    response = requests.post(
        url=GRAPHQL_ENDPOINT,
        json={"query": query},
    ).json()
    return response["data"]["all_books"]["edges"]


def main():
    while True:
        books = fetch_data()
        logging.info(f"Got data with length {len(books)}")

        # Process in batches to avoid memory bloat
        for i in range(0, len(books), BATCH_SIZE):
            batch = books[i : i + BATCH_SIZE]
            process_batch(batch)


if __name__ == "__main__":
    main()
