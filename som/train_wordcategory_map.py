import os
import logging
import somoclu
import numpy as np
import datetime
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from scipy import sparse
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
documents_directory = PARENT_DIR / "data"
documents = load_documents_list(documents_directory)

# Step 2: Split each document into smaller parts (e.g., paragraphs)
all_paragraphs = []
for doc in documents:
    all_paragraphs.extend(doc.split("\n\n"))  # You can adjust this splitting logic

# Step 3: Create the vocabulary
# Use all paragraphs to create a vocabulary first
vectorizer = CountVectorizer(min_df=50, stop_words="english")
logging.info(f"Fitting monogran vectorizer ...")
vectorizer.fit(all_paragraphs)  # Only fit the vectorizer to get the vocabulary
vocabulary = vectorizer.vocabulary_  # Extract the vocabulary


# Step 4: Create Document-Term Matrix in chunks
# https://medium.com/@AgenceSkoli/how-to-avoid-memory-overloads-using-scikit-learn-f5eb911ae66c
def getchunks(data, chunk_size):
    """Yield successive chunks from data."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


chunk_size = 10000  # Adjust chunk size based on memory constraints
dtm_chunked = []
vectorizer_chunked = CountVectorizer(vocabulary=vocabulary, stop_words="english")

logging.info(f"Chunking monogram ...")
for chunk in getchunks(all_paragraphs, chunk_size):
    dtm_chunk = vectorizer_chunked.transform(chunk)  # Use the vocabulary in transform
    dtm_chunked.append(dtm_chunk)

# Concatenate all sparse matrices to get the final DTM
logging.info(f"Vstacking monogram ...")
dtm = sparse.vstack(dtm_chunked)

# Step 5: Sum up the word occurrences across all documents
word_occurrences = pd.DataFrame(
    data=dtm.sum(axis=0).A, columns=vectorizer.get_feature_names_out()  # Keep 2D
)

# Step 6: Process Bigrams similarly
vectorizer_bigram = CountVectorizer(
    ngram_range=(2, 2), min_df=50, stop_words="english", vocabulary=None
)
logging.info(f"Fitting bigran vectorizer ...")
vectorizer_bigram.fit(all_paragraphs)  # Fit bigram vectorizer
vocabulary_bigram = vectorizer_bigram.vocabulary_

# Process bigrams in chunks
dtm_bigram_chunked = []
vectorizer_bigram_chunked = CountVectorizer(
    vocabulary=vocabulary_bigram, ngram_range=(2, 2), stop_words="english"
)

logging.info(f"Chunking bigram ...")
for chunk in getchunks(all_paragraphs, chunk_size):
    dtm_bigram_chunk = vectorizer_bigram_chunked.transform(
        chunk
    )  # Use the bigram vocabulary
    dtm_bigram_chunked.append(dtm_bigram_chunk)

# Concatenate the bigram DTMs
logging.info(f"Vstacking bigram ...")
dtm_bigram = sparse.vstack(dtm_bigram_chunked)

# Step 7: Sum up bigram occurrences across all documents
bigram_occurrences = pd.DataFrame(
    data=dtm_bigram.sum(axis=0).A,  # Keep 2D
    columns=vectorizer_bigram.get_feature_names_out(),
)
# Step 1: Get the number of columns (terms) from dtm_df
num_columns = word_occurrences.shape[1]

# Step 2: Create a DataFrame with 90 rows and random values (between 0.0 and 1.0) for each word
word_df = pd.DataFrame(np.random.uniform(0.0, 1.0, size=(90, num_columns)))

# Step 3: Assign the column names of dtm_df to the new word_df
word_df.columns = word_occurrences.columns

kaski_df = encode_kaski(word_df, bigram_occurrences)

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
