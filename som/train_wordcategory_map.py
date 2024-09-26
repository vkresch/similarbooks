import os
import logging
import somoclu
import numpy as np
import datetime
import pandas as pd
from Scaler import Scaler
from time import perf_counter
from pathlib import Path
import pickle
from som.utils import (
    encode_kaski,
    preprocess_text,
    load_documents_list,
    process_documents,
    filter_rare_terms,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent


def main():
    documents_directory = PARENT_DIR / "data/archive_books"

    # Step 1: Process monograms
    logging.info("Processing monograms...")
    dtm_mono, feature_names_mono = process_documents(
        documents_directory, ngram_range=(1, 1), min_df=1
    )

    # Step 2: Filter rare terms
    logging.info("Filtering rare monogram terms...")
    dtm_mono, feature_names_mono = filter_rare_terms(
        dtm_mono, feature_names_mono, min_df=50
    )

    # Step 3: Sum up monogram occurrences
    logging.info("Summing up monogram occurrences...")
    word_occurrences = pd.DataFrame(
        dtm_mono.sum(axis=0).A1, index=feature_names_mono, columns=["occurrences"]
    )

    # Step 4: Process bigrams
    logging.info("Processing bigrams...")
    dtm_bigram, feature_names_bigram = process_documents(
        documents_directory, ngram_range=(2, 2), min_df=1
    )

    # Step 5: Filter rare bigram terms
    logging.info("Filtering rare bigram terms...")
    dtm_bigram, feature_names_bigram = filter_rare_terms(
        dtm_bigram, feature_names_bigram, min_df=50
    )

    # Step 6: Sum up bigram occurrences
    logging.info("Summing up bigram occurrences...")
    bigram_occurrences = pd.DataFrame(
        dtm_bigram.sum(axis=0).A1, index=feature_names_bigram, columns=["occurrences"]
    )

    # Step 5: Create word_df
    num_columns = len(feature_names_mono)
    word_df = pd.DataFrame(
        np.random.uniform(0.0, 1.0, size=(90, num_columns)), columns=feature_names_mono
    )

    # Step 6: Encode using Kaski method
    logging.info("Encoding using Kaski method...")
    kaski_df = encode_kaski(word_df, bigram_occurrences)

    # Step 7: Scale data
    scaler = Scaler()
    data_train_matrix = scaler.scale(kaski_df).T

    logging.info(f"Data shape: {data_train_matrix.shape}")

    # Step 8: Train SOM
    som = somoclu.Somoclu(
        15,
        21,
        compactsupport=True,
        maptype="toroid",
        verbose=2,
        initialization="pca",
    )

    t1_start = perf_counter()
    logging.info(f"Training start: {datetime.datetime.now()}")
    som.train(
        data=data_train_matrix.to_numpy(dtype="float32"),
        epochs=500,
        radiuscooling="exponential",
        scalecooling="exponential",
    )
    logging.info(f"Training finished: {datetime.datetime.now()}")

    t1_stop = perf_counter()
    delta_seconds = t1_stop - t1_start
    logging.info(f"Elapsed time for training in seconds: {delta_seconds}")
    logging.info(f"Elapsed time for training in minutes: {delta_seconds / 60.0}")
    logging.info(f"Elapsed time for training in hours: {delta_seconds / 3600.0}")

    som.labels = dict(zip(data_train_matrix.index, som.bmus))

    with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "wb") as file_model:
        som.name = f"wordcategory"
        pickle.dump(som, file_model, pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    main()
