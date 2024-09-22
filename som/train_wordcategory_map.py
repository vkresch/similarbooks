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
from som.utils import encode_kaski, preprocess_text, load_documents_list

import numpy as np
import pandas as pd


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent

# Use a directory that contains all your text documents
documents_directory = PARENT_DIR / "data/gutenberg_books"
documents = load_documents_list(documents_directory)

# Step 2: Split each document into smaller parts (e.g., paragraphs)
all_paragraphs = []
for doc in documents:
    all_paragraphs.extend(doc.split("\n\n"))  # You can adjust this splitting logic


# Step 2: Create a Document-Term Matrix
vectorizer = CountVectorizer(
    min_df=20, stop_words="english"
)  # min_df=200 removes words occurring <50 times
dtm = vectorizer.fit_transform(all_paragraphs)

# Step 3: Convert the DTM to a DataFrame for easier viewing
dtm_df = pd.DataFrame(dtm.toarray(), columns=vectorizer.get_feature_names_out())
# logging.info(dtm_df.head())  # Display the first few rows of the DTM

# Step 4: Sum up the word occurrences across all documents
word_occurrences = dtm_df.sum(axis=0)

# Display the word occurrences
word_occurrences_sorted = word_occurrences.sort_values(
    ascending=False
)  # Sort by frequency (optional)
# logging.info(word_occurrences_sorted)  # Display the top 10 most frequent words

# Step 1: Create a Bigram Document-Term Matrix
vectorizer_bigram = CountVectorizer(
    ngram_range=(2, 2), min_df=20, stop_words="english"
)  # Set ngram_range=(2, 2) for bigrams
dtm_bigram = vectorizer_bigram.fit_transform(all_paragraphs)

# Step 2: Convert the Bigram DTM to a DataFrame
dtm_bigram_df = pd.DataFrame(
    dtm_bigram.toarray(), columns=vectorizer_bigram.get_feature_names_out()
)
logging.info(dtm_bigram_df)

# Step 3: Sum up the bigram occurrences across all documents
bigram_occurrences = dtm_bigram_df.sum(axis=0).to_frame().T
logging.info(bigram_occurrences)

# Step 4: Sort and display the top 10 most frequent bigrams
# bigram_occurrences_sorted = bigram_occurrences.sort_values(ascending=False)
# logging.info(bigram_occurrences_sorted)  # Display the top 10 most frequent bigrams

# Step 1: Get the number of columns (terms) from dtm_df
num_columns = dtm_df.shape[1]

# Step 2: Create a DataFrame with 90 rows and random values (between 0.0 and 1.0) for each word
word_df = pd.DataFrame(np.random.uniform(0.0, 1.0, size=(90, num_columns)))

# Step 3: Assign the column names of dtm_df to the new word_df
word_df.columns = dtm_df.columns

logging.info(word_df)

kaski_df = encode_kaski(word_df, bigram_occurrences)

scaler = Scaler()
data_train_matrix = scaler.scale(kaski_df).T

logging.info(f"Data shape: {data_train_matrix.shape}")
som = somoclu.Somoclu(
    50,
    50,
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

som.labels = data_train_matrix.index

with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "wb") as file_model:
    som.name = f"wordcategory"
    pickle.dump(som, file_model, pickle.HIGHEST_PROTOCOL)
