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
from som.utils import encode_kaski, preprocess_text, load_documents_dict

import numpy as np
import pandas as pd


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent

documents_directory = PARENT_DIR / "data/gutenberg_books"
documents = load_documents_dict(documents_directory)

with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "rb") as file_model:
    wordcategory_som = pickle.load(file_model)

dtm_dict = {}

for filename, text in documents.items():
    vectorizer = CountVectorizer(
        min_df=1, stop_words="english"
    )  # min_df=200 removes words occurring <50 times
    dtm_dict[filename] = {
        "vectorizer": vectorizer,
        "matrix": vectorizer.fit_transform([text]),
    }

# dtm_df = pd.DataFrame(dtm_dict["1"]["matrix"].toarray(), columns=dtm_dict["1"]["vectorizer"].get_feature_names_out())
# print(dtm_df)
