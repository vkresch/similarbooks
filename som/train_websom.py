import os
import logging
import somoclu
import numpy as np
import datetime
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from Scaler import Scaler
from time import perf_counter
from pathlib import Path
import pickle
from tqdm import tqdm  # For progress bar
from som.utils import (
    encode_kaski,
    preprocess_text,
    load_documents_dict,
    get_hit_histogram,
    draw_barchart,
    query_training_data,
)
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent

with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "rb") as file_model:
    wordcategory_som = pickle.load(file_model)

if os.path.exists(PARENT_DIR / Path(f"models/hit_df.pkl")):
    logging.info(f"Loading already processed hit_df ...")
    with open(PARENT_DIR / Path(f"models/hit_df.pkl"), "rb") as file_model:
        hit_df = pickle.load(file_model)
else:
    logging.info(f"Generating hit histogram ...")
    summaries = query_training_data(limited=False)
    hit_data = []  # To collect rows for hit_df
    for book in tqdm(summaries):
        # Vectorize the text using CountVectorizer
        vectorizer = CountVectorizer(
            min_df=1, stop_words="english"
        )  # Adjust min_df to remove infrequent words if necessary

        # Generate document-term matrix
        try:
            dtm = vectorizer.fit_transform(
                [book.get("node").get("title") + " " + book.get("node").get("summary")]
            )  # text should be a single string, hence [text]
        except Exception as e:
            continue

        # Sum word occurrences across the document and keep sparse format
        word_occurrences = pd.DataFrame(
            dtm.sum(axis=0).A1,  # A1 gives a flat dense array from sparse matrix
            index=vectorizer.get_feature_names_out(),
            columns=[
                book.get("node").get("book_id")
            ],  # Column for the filename to track the document
        ).T  # Transpose to make words columns, filename as row

        # Compute the hit histogram using your custom function
        hit_histogram = get_hit_histogram(wordcategory_som, word_occurrences)
        # draw_barchart(filename, hit_histogram)

        # Ensure hit_histogram is a DataFrame
        if isinstance(hit_histogram, np.ndarray):
            hit_histogram = pd.DataFrame(
                [hit_histogram]
            )  # Convert array to DataFrame and use a list to create one row

        # Add the filename as the index of the hit_histogram DataFrame
        hit_histogram.index = [book.get("node").get("book_id")]

        # Append the hit_histogram DataFrame to hit_data
        hit_data.append(hit_histogram)

    # Concatenate all hit_histogram DataFrames into a single DataFrame
    hit_df = pd.concat(hit_data)

    with open(PARENT_DIR / Path(f"models/hit_df.pkl"), "wb") as file_model:
        pickle.dump(hit_df, file_model, pickle.HIGHEST_PROTOCOL)

scaler = Scaler()
train_data = scaler.scale(hit_df.T).T

with open(PARENT_DIR / Path(f"models/websom_scaler.pkl"), "wb") as file_model:
    pickle.dump(scaler, file_model, pickle.HIGHEST_PROTOCOL)

logging.info(f"Data shape: {train_data.shape}")
som = somoclu.Somoclu(
    100,
    100,
    compactsupport=True,
    maptype="toroid",
    verbose=2,
    initialization="pca",
)

# Start the stopwatch / counter
t1_start = perf_counter()
logging.info(f"Training start: {datetime.datetime.now()}")
som.train(
    data=train_data.to_numpy(dtype="float32"),
    epochs=500,
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

som.labels = dict(zip(train_data.index, som.bmus))

with open(PARENT_DIR / Path(f"models/websom.pkl"), "wb") as file_model:
    som.name = f"websom"
    pickle.dump(som, file_model, pickle.HIGHEST_PROTOCOL)
