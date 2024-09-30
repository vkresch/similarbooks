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
from som.utils import (
    encode_kaski,
    preprocess_text,
    load_documents_list,
    query_training_data,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent

if os.path.exists(PARENT_DIR / Path(f"models/word_occurrences.pkl")) and os.path.exists(
    PARENT_DIR / Path(f"models/bigram_occurrences.pkl")
):
    logging.info(f"Loading already processed monogram and bigram dtm ...")
    with open(PARENT_DIR / Path(f"models/word_occurrences.pkl"), "rb") as file_model:
        word_occurrences = pickle.load(file_model)

    with open(PARENT_DIR / Path(f"models/bigram_occurrences.pkl"), "rb") as file_model:
        bigram_occurrences = pickle.load(file_model)
else:
    # summaries_dict = query_training_data(limited=False)
    # summaries = [item.get("node").get("summary") for item in summaries_dict]

    documents_directory = PARENT_DIR / "data/"
    summaries = load_documents_list(documents_directory, max_documents=55_000)

    # Step 2: Create a Document-Term Matrix
    vectorizer = CountVectorizer(
        min_df=200, stop_words="english"
    )  # min_df=50 removes words occurring <50 times
    logging.info(f"Fitting monogram vectorizer ...")
    dtm = vectorizer.fit_transform(summaries)

    # Step 4: Sum up the word occurrences across all summaries
    word_occurrences = pd.DataFrame(
        dtm.sum(axis=0).flatten(), columns=vectorizer.get_feature_names_out()
    )

    with open(PARENT_DIR / Path(f"models/word_occurrences.pkl"), "wb") as file_model:
        pickle.dump(word_occurrences, file_model, pickle.HIGHEST_PROTOCOL)

    # Step 1: Create a Bigram Document-Term Matrix
    vectorizer_bigram = CountVectorizer(
        ngram_range=(2, 2), min_df=200, stop_words="english"
    )  # Set ngram_range=(2, 2) for bigrams
    logging.info(f"Fitting bigram vectorizer ...")
    dtm_bigram = vectorizer_bigram.fit_transform(summaries)

    # Step 3: Sum up the bigram occurrences across all summaries
    bigram_occurrences = pd.DataFrame(
        dtm_bigram.sum(axis=0).flatten(),
        columns=vectorizer_bigram.get_feature_names_out(),
    )

    with open(PARENT_DIR / Path(f"models/bigram_occurrences.pkl"), "wb") as file_model:
        pickle.dump(bigram_occurrences, file_model, pickle.HIGHEST_PROTOCOL)

# Step 1: Get the number of columns (terms) from dtm_df
num_columns = word_occurrences.shape[1]

# Step 2: Create a DataFrame with 90 rows and random values (between 0.0 and 1.0) for each word
word_df = pd.DataFrame(np.random.uniform(0.0, 1.0, size=(90, num_columns)))

# Step 3: Assign the column names of dtm_df to the new word_df
word_df.columns = word_occurrences.columns

if os.path.exists(PARENT_DIR / Path(f"models/kaski_df.pkl")):
    logging.info(f"Loading already encoded kaski df ...")
    with open(PARENT_DIR / Path(f"models/kaski_df.pkl"), "rb") as file_model:
        kaski_df = pickle.load(file_model)
else:
    kaski_df = encode_kaski(word_df, bigram_occurrences)
    with open(PARENT_DIR / Path(f"models/kaski_df.pkl"), "wb") as file_model:
        pickle.dump(kaski_df, file_model, pickle.HIGHEST_PROTOCOL)

scaler = Scaler()
data_train_matrix = scaler.scale(kaski_df).T

logging.info(f"Data shape: {data_train_matrix.shape}")
# Wordcategory Map 15 x 21
# https://static.aminer.org/pdf/PDF/000/916/142/websom_self_organizing_maps_of_document_collections.pdf
som = somoclu.Somoclu(
    15,
    21,
    compactsupport=True,
    maptype="toroid",
    verbose=2,
    initialization="pca",
)

# Start the stopwatch / counter
t1_start = perf_counter()
logging.info(f"Training start: {datetime.datetime.now()}")
som.train(
    data=data_train_matrix.to_numpy(dtype="float32"),
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

som.labels = dict(zip(data_train_matrix.index, som.bmus))

with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "wb") as file_model:
    som.name = f"wordcategory"
    pickle.dump(som, file_model, pickle.HIGHEST_PROTOCOL)
