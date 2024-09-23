import os
import sys
import re
import pickle
import pymongo
import logging
import datetime
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm  # For progress bar
from pathlib import Path
import som.Scaler as Scaler
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)
from app.similarbooks.config import Config

PARENT_DIR = Path(__file__).resolve().parent


def load_file(path):
    with open(path, "rb") as file_model:
        obj = pickle.load(file_model)
    return obj


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
    # Dimensions of the word_df (used to create feature_df)
    word_encoding_length, word_number_length = word_df.shape

    # Initialize the feature DataFrame (twice the rows of word_df)
    feature_df = pd.DataFrame(
        np.zeros((word_encoding_length * 2, word_number_length)),
        columns=word_df.columns,
    )

    logging.info(f"Encoding words...")

    # Progress bar
    word_names = word_df.columns
    for cnames in tqdm(word_names, total=word_number_length):
        # Match bigrams that contain the word (cnames) as the first word
        match_all = [
            bool(re.search(rf"\b{cnames}\b", bigram, flags=re.IGNORECASE))
            for bigram in bigram_occurrences.columns
        ]
        all_match_bigrams = bigram_occurrences.loc[:, match_all]

        # Ensure all_match_bigrams is a DataFrame, even if it contains a single column
        if isinstance(all_match_bigrams, pd.Series):
            all_match_bigrams = all_match_bigrams.to_frame()

        # Match bigrams where 'cnames' is the first word
        match_names_first = [
            bool(re.match(rf"^{cnames} ", bigram, flags=re.IGNORECASE))
            for bigram in all_match_bigrams.columns
        ]
        word_set_first = all_match_bigrams.loc[:, match_names_first]
        if isinstance(word_set_first, pd.Series):  # Ensure DataFrame even if one column
            word_set_first = word_set_first.to_frame()

        word_set_names_first = [
            re.sub(rf"^{cnames} ", "", bigram) for bigram in word_set_first.columns
        ]
        word_sum_count_first = word_set_first.sum().sum()

        word_sum_vector_first = np.zeros(word_encoding_length)
        for word, bigram_col in zip(word_set_names_first, word_set_first.columns):
            word_vector = (
                word_df[word]
                if word in word_df.columns
                else np.zeros(word_encoding_length)
            )
            word_count = word_set_first[bigram_col].sum()
            word_sum_vector_first += word_count * word_vector
        E_first = (
            word_sum_vector_first / word_sum_count_first
            if word_sum_count_first != 0
            else np.zeros(word_encoding_length)
        )

        # Match bigrams where 'cnames' is the last word
        match_names_last = [
            bool(re.search(rf" {cnames}$", bigram, flags=re.IGNORECASE))
            for bigram in all_match_bigrams.columns
        ]
        word_set_last = all_match_bigrams.loc[:, match_names_last]
        if isinstance(word_set_last, pd.Series):  # Ensure DataFrame even if one column
            word_set_last = word_set_last.to_frame()

        word_set_names_last = [
            re.sub(rf" {cnames}$", "", bigram) for bigram in word_set_last.columns
        ]
        word_sum_count_last = word_set_last.sum().sum()

        word_sum_vector_last = np.zeros(word_encoding_length)
        for word, bigram_col in zip(word_set_names_last, word_set_last.columns):
            word_vector = (
                word_df[word]
                if word in word_df.columns
                else np.zeros(word_encoding_length)
            )
            word_count = word_set_last[bigram_col].sum()
            word_sum_vector_last += word_count * word_vector
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


def get_hit_histogram(som, dtm):
    rows, columns = som.umatrix.shape
    node_numbers = rows * columns
    hit_histogram = np.zeros(node_numbers)
    terms = dtm.columns
    for term in terms:
        bmu = som.labels.get(term)
        if bmu is not None:
            index = bmu[1] * columns + bmu[0]
            hit_histogram[index] = dtm[term]
    return hit_histogram


def load_documents_list(directory):
    logging.info(f"Loading documents ...")
    documents = []
    for filepath in tqdm(Path(directory).glob("*.txt")):
        with open(filepath, "r", encoding="utf-8") as file:
            text = file.read()
            cleaned_text = preprocess_text(text)
            documents.extend(cleaned_text.split("\n\n"))
    return documents


def load_documents_dict(directory):
    logging.info(f"Loading documents ...")
    documents = {}
    for filepath in tqdm(Path(directory).glob("*.txt")):
        with open(filepath, "r", encoding="utf-8") as file:
            text = file.read()
            cleaned_text = preprocess_text(text)
            filepath = os.path.basename(filepath)
            filename = os.path.splitext(filepath)[0]
            documents[filename] = cleaned_text.split("\n\n")
    return documents
