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
from som.utils import preprocess_text, get_top_bmus, model_dict, get_surface_state

PARENT_DIR = Path(__file__).resolve().parent

sys.modules["Scaler"] = Scaler

with open(
    PARENT_DIR / Path(f"data/archive_books/A_UID_Numbering_Scheme.txt"), "r"
) as file_model:
    text = file_model.read()
    preprocessed_text_ab = preprocess_text(text)

with open(PARENT_DIR / Path(f"data/gutenberg_books/1.txt"), "r") as file_model:
    text = file_model.read()
    preprocessed_text_gb = preprocess_text(text)

tasks_vectorized = model_dict["vectorizer"].transform(
    [preprocessed_text_ab, preprocessed_text_gb]
)
tasks_topic_dist = model_dict["lda"].transform(tasks_vectorized)
active_map = model_dict["lda_websom"].get_surface_state(data=tasks_topic_dist)
print(active_map)

bmu_nodes = get_top_bmus(model_dict["lda_websom"], active_map, top_n=1)
print(bmu_nodes)
