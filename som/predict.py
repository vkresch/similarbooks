import sys
import requests
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import pickle
from pathlib import Path
from dash import dash_table
import Scaler as Scaler
from sklearn.feature_extraction.text import CountVectorizer
from som.utils import get_hit_histogram, preprocess_text, get_top_bmus

PARENT_DIR = Path(__file__).resolve().parent

sys.modules["Scaler"] = Scaler

with open(
    PARENT_DIR / Path(f"data/archive_books/A_UID_Numbering_Scheme.txt"), "r"
) as file_model:
    text = file_model.read()
    preprocessed_text = preprocess_text(text)

with open(PARENT_DIR / Path(f"models/websom_scaler.pkl"), "rb") as file_model:
    scaler = pickle.load(file_model)

with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "rb") as file_model:
    wordcategory_som = pickle.load(file_model)

with open(PARENT_DIR / Path(f"models/websom.pkl"), "rb") as file_model:
    websom = pickle.load(file_model)

vectorizer = CountVectorizer(
    min_df=1, stop_words="english"
)  # Adjust min_df to remove infrequent words if necessary
dtm = vectorizer.fit_transform([preprocessed_text])

# Sum word occurrences across the document and keep sparse format
word_occurrences = pd.DataFrame(
    dtm.sum(axis=0).A1,  # A1 gives a flat dense array from sparse matrix
    index=vectorizer.get_feature_names_out(),
    columns=["xxxx"],  # Column for the filename to track the document
).T  # Transpose to make words columns, filename as row
hit_histogram = get_hit_histogram(wordcategory_som, word_occurrences)
active_map = websom.get_surface_state(data=hit_histogram)
bmu_nodes = get_top_bmus(websom, active_map, top_n=1)

print(bmu_nodes)
