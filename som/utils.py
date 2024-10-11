import os
import sys
import re
import pickle
import pymongo
import json
import logging
import datetime
import random
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm  # For progress bar
from pathlib import Path
import som.Scaler as Scaler
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.distance import jensenshannon
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)
from app.similarbooks.config import Config

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent


def load_file(path):
    with open(path, "rb") as file_model:
        obj = pickle.load(file_model)
    return obj


model_dict = {
    "lda_websom": load_file(f"som/models/lda_websom.pkl"),
    # "doc_topic_dist": load_file(f"som/models/doc_topic_dist.pkl"),
    "vectorizer": load_file(f"som/models/lda_vectorizer.pkl"),
    "lda": load_file(f"som/models/lda.pkl"),
}


def get_similar_books_lda(text, top_n=10):
    # Vectorize the input text
    tasks_vectorized = model_dict.get("vectorizer").transform([text])
    # Get the topic distribution for the input text
    tasks_topic_dist = model_dict.get("lda").transform(tasks_vectorized)[0]

    # Get document topic distributions
    df = model_dict.get("doc_topic_dist")

    logging.info("Calculating distances ....")
    # Calculate Jensen-Shannon distance for all documents at once using NumPy
    distances = np.apply_along_axis(
        lambda x: jensenshannon(x, tasks_topic_dist), 1, df.values
    )

    logging.info("Getting k nearest ....")
    # Get the top N nearest books
    k_nearest = np.argsort(distances)[:top_n]

    return list(df.index[k_nearest])


# Function to parse the desired information
def parse_gutenberg_info(file_path):
    # Dictionary to store parsed information
    info = {
        "Title": None,
        "Author": None,
        "Release Date": None,
        "Language": None,
        "Produced by": None,
    }

    # Open the text file and read the lines
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            # Check each line for the desired fields and extract values
            if line.startswith("Title:"):
                info["Title"] = line.split("Title:")[1].strip()
            elif line.startswith("Author:"):
                info["Author"] = line.split("Author:")[1].strip()
            elif line.startswith("Release Date:"):
                info["Release Date"] = line.split("Release Date:")[1].strip()
            elif line.startswith("Language:"):
                info["Language"] = line.split("Language:")[1].strip()
            elif line.startswith("Produced by:"):
                info["Produced by"] = line.split("Produced by:")[1].strip()

    return info


def draw_barchart(filename, hit_histogram):

    x = np.arange(len(hit_histogram))
    plt.bar(x, hit_histogram)

    # Add labels and title
    plt.xlabel("Nodes")
    plt.ylabel("Word Hits")
    plt.title("Word Category Map Hits")

    # Display the histogram
    plt.savefig(PARENT_DIR / Path(f"hist_{filename}.png"))


def encode_kaski(word_df, bigram_occurrences):
    word_encoding_length, word_number_length = word_df.shape
    feature_df = pd.DataFrame(
        np.zeros((word_encoding_length * 2, word_number_length)),
        columns=word_df.columns,
    )
    logging.info("Encoding words with kaski ...")

    word_names = word_df.columns
    bigram_columns = bigram_occurrences.columns

    # Precompute regex patterns
    first_word_patterns = {
        word: re.compile(rf"^{word} ", flags=re.IGNORECASE) for word in word_names
    }
    last_word_patterns = {
        word: re.compile(rf" {word}$", flags=re.IGNORECASE) for word in word_names
    }

    for cnames in tqdm(word_names, total=word_number_length):
        # Match bigrams that contain the word (cnames)
        match_all = [
            bool(re.search(rf"\b{cnames}\b", bigram, flags=re.IGNORECASE))
            for bigram in bigram_columns
        ]
        all_match_bigrams = bigram_occurrences.loc[:, match_all]

        # Process first word matches
        match_names_first = [
            bool(first_word_patterns[cnames].match(bigram))
            for bigram in all_match_bigrams.columns
        ]
        word_set_first = all_match_bigrams.loc[:, match_names_first]
        word_set_names_first = [
            first_word_patterns[cnames].sub("", bigram)
            for bigram in word_set_first.columns
        ]

        word_sum_count_first = word_set_first.values.sum()
        word_sum_vector_first = np.sum(
            [
                (
                    word_df[word].values * word_set_first[bigram].sum()
                    if word in word_df.columns
                    else 0
                )
                for word, bigram in zip(word_set_names_first, word_set_first.columns)
            ],
            axis=0,
        )
        E_first = (
            word_sum_vector_first / word_sum_count_first
            if word_sum_count_first != 0
            else np.zeros(word_encoding_length)
        )

        # Process last word matches
        match_names_last = [
            bool(last_word_patterns[cnames].search(bigram))
            for bigram in all_match_bigrams.columns
        ]
        word_set_last = all_match_bigrams.loc[:, match_names_last]
        word_set_names_last = [
            last_word_patterns[cnames].sub("", bigram)
            for bigram in word_set_last.columns
        ]

        word_sum_count_last = word_set_last.values.sum()
        word_sum_vector_last = np.sum(
            [
                (
                    word_df[word].values * word_set_last[bigram].sum()
                    if word in word_df.columns
                    else 0
                )
                for word, bigram in zip(word_set_names_last, word_set_last.columns)
            ],
            axis=0,
        )
        E_last = (
            word_sum_vector_last / word_sum_count_last
            if word_sum_count_last != 0
            else np.zeros(word_encoding_length)
        )

        # Update feature_df with the computed values
        feature_df[cnames] = np.concatenate((E_first, E_last))

    logging.info("Finished encoding words!")
    return feature_df


def preprocess_text(text):
    # Remove non-ASCII characters
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Remove special characters and numbers
    text = re.sub(r"[,:.{[}\'\"\]]", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"_", "", text)
    text = re.sub(r":", "", text)
    text = re.sub(r"'", "", text)

    # Convert text to lowercase
    text = text.lower()

    # Remove emails and URLs
    text = re.sub(r"\S+@\S+", "", text)  # Emails
    text = re.sub(r"http\S+|www\S+", "", text)  # URLs

    # Remove trailing and leading whitespaces
    text = text.strip()

    return text


def gaussian_blur(histogram):
    FWHM = 2

    # Calculate the standard deviation for the Gaussian kernel
    sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))

    # Apply Gaussian filter to blur the histogram
    return gaussian_filter1d(histogram, sigma=sigma)


def min_max_scaling(array):
    # Min-Max scaling
    min_val = np.min(array)
    max_val = np.max(array)

    # Check if max_val and min_val are the same to avoid division by zero
    if max_val == min_val:
        # Set scaled array to zeros (or any constant value)
        scaled_array = np.zeros_like(array)
    else:
        scaled_array = (array - min_val) / (max_val - min_val)

    return scaled_array


def get_hit_histogram(som, dtm):
    rows, columns = som.umatrix.shape
    node_numbers = rows * columns
    hit_histogram = np.zeros(node_numbers)
    terms = dtm.columns
    for term in terms:
        bmu = som.labels.get(term)
        if bmu is not None:
            index = bmu[1] * columns + bmu[0]
            hit_histogram[index] += dtm[term]
    return min_max_scaling(gaussian_blur(hit_histogram))


def get_document_text(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        text = file.read()
        return preprocess_text(text)


def load_documents_list(directory, max_documents=40000):
    logging.info(f"Loading documents recursively from {directory}...")
    filepaths = list(Path(directory).rglob("*.txt"))
    random.shuffle(filepaths)
    limited_filepaths = filepaths[:max_documents]
    documents = [get_document_text(filepath) for filepath in tqdm(limited_filepaths)]
    return documents


def load_documents_dict(directory, max_documents=40000):
    logging.info(f"Loading documents recursively from {directory}...")
    filepaths = list(Path(directory).rglob("*.txt"))
    random.shuffle(filepaths)
    limited_filepaths = filepaths[:max_documents]
    documents = {
        os.path.splitext(os.path.basename(filepath))[0]: [get_document_text(filepath)]
        for filepath in tqdm(limited_filepaths)
    }
    return documents


def load_documents_graphql(directory, max_documents=100_000):
    logging.info(f"Loading documents recursively from {directory}...")
    filepaths = list(Path(directory).rglob("*.txt"))
    random.shuffle(filepaths)
    limited_filepaths = filepaths[:max_documents]
    documents = [
        {
            "node": {
                "book_id": (
                    f"gb_{os.path.splitext(os.path.basename(filepath))[0]}"
                    if "gutenberg_books" in str(filepath)
                    else os.path.splitext(os.path.basename(filepath))[0]
                ),
                "title": "",
                "summary": get_document_text(filepath),
            }
        }
        for filepath in tqdm(limited_filepaths)
    ]
    return documents


TRAIN_SOM_QUERY = """
{{
  all_books (filters: {0}, per_page: {1}) {{
    edges {{
      node {{
        sha,
        title,
        summary,
      }}
    }}
  }}
}}""".strip()

UNLIMITED_TRAIN_SOM_QUERY = """
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


def query_training_data(per_page=500, limited=True):
    logging.info("Getting data ...")
    query = (
        TRAIN_SOM_QUERY.format(
            '{summary_length_gte: 400, language: "English", spider: "goodreads"}',
            per_page,
        )
        if limited
        else UNLIMITED_TRAIN_SOM_QUERY.format(
            '{summary_length_gte: 400, language: "English", spider: "goodreads"}'
        )
    )
    logging.info(f"Query: {query}")
    response = requests.post(
        url=GRAPHQL_ENDPOINT,
        json={"query": query},
    ).json()
    books = response["data"]["all_books"]["edges"]
    if len(books) == 0:
        raise Exception(f"No books found for the following query: {query}")
    return books


DEBUG_SOM_QUERY = """
{{
  all_books (filters: {0}) {{
    edges {{
      node {{
        book_id,
        title,
        author,
        summary,
      }}
    }}
  }}
}}""".strip()


def query_debug_display(sha_list):
    logging.info("Getting data ...")
    query = DEBUG_SOM_QUERY.format(
        "{{sha_in: {0}, summary_exists: true}}".format(json.dumps(sha_list))
    )
    logging.info(f"Query: {query}")
    response = requests.post(
        url=GRAPHQL_ENDPOINT,
        json={"query": query},
    ).json()
    books = response["data"]["all_books"]["edges"]
    if len(books) == 0:
        raise Exception(f"No books found for the following query: {query}")
    return books


def get_top_bmus(som, activation_map, top_n):
    """Returns the top n matching units.

    :param activation_map: Activation map computed with som.get_surface_state()
    :type activation_map: 2D numpy.array

    :returns: The bmus indexes and the second bmus indexes corresponding to
              this activation map (same as som.bmus for the training samples).
    :rtype: tuple of 2D numpy.array
    """

    # Normal BMU finding
    if top_n == 1:
        return som.get_bmus(activation_map)

    n_samples = activation_map.shape[0]
    top_bmus_combined = np.empty((n_samples, top_n, 2), dtype=int)
    for n in range(top_n):
        # Get the BMU indices
        bmu_indices = activation_map.argmin(axis=1)
        Y, X = np.unravel_index(bmu_indices, (som._n_rows, som._n_columns))
        top_bmus_combined[:, n, :] = np.vstack((X, Y)).T

        # Mask the BMU values
        activation_map[np.arange(n_samples), bmu_indices] = np.inf

    return top_bmus_combined[0]
