import os
import logging
import somoclu
import numpy as np
import datetime
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction import text
from sklearn.decomposition import LatentDirichletAllocation
from scipy.spatial.distance import jensenshannon

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
summaries_dict = query_training_data(limited=False)
if os.path.exists(PARENT_DIR / Path(f"models/lda_dtm.pkl")):
    logging.info(f"Loading already encoded DTM models ...")
    with open(PARENT_DIR / Path(f"models/lda_vectorizer.pkl"), "rb") as file_model:
        vectorizer = pickle.load(file_model)
    with open(PARENT_DIR / Path(f"models/lda_dtm.pkl"), "rb") as file_model:
        dtm = pickle.load(file_model)
else:
    summaries = [
        item.get("node").get("title") + " " + item.get("node").get("summary")
        for item in summaries_dict
    ]

    # Step 2: Create a Document-Term Matrix
    vectorizer = CountVectorizer(
        min_df=2, stop_words="english"
    )  # min_df=10 removes words occurring <50 times
    logging.info(f"Fitting monogram vectorizer ...")
    dtm = vectorizer.fit_transform(summaries)

    with open(PARENT_DIR / Path(f"models/lda_vectorizer.pkl"), "wb") as file_model:
        pickle.dump(vectorizer, file_model, pickle.HIGHEST_PROTOCOL)

    with open(PARENT_DIR / Path(f"models/lda_dtm.pkl"), "wb") as file_model:
        pickle.dump(dtm, file_model, pickle.HIGHEST_PROTOCOL)

if os.path.exists(PARENT_DIR / Path(f"models/lda.pkl")):
    logging.info(f"Loading already encoded LDA models ...")
    with open(PARENT_DIR / Path(f"models/lda.pkl"), "rb") as file_model:
        lda = pickle.load(file_model)
else:
    lda = LatentDirichletAllocation(n_components=100, random_state=42)
    lda.fit(dtm)

    with open(PARENT_DIR / Path(f"models/lda.pkl"), "wb") as file_model:
        pickle.dump(lda, file_model, pickle.HIGHEST_PROTOCOL)

if os.path.exists(PARENT_DIR / Path(f"models/doc_topic_dist.pkl")):
    logging.info(f"Loading document distance data frame ...")
    with open(PARENT_DIR / Path(f"models/doc_topic_dist.pkl"), "rb") as file_model:
        doc_topic_dist = pickle.load(file_model)
else:
    doc_topic_dist = pd.DataFrame(
        lda.transform(dtm),
        index=[item.get("node").get("book_id") for item in summaries_dict],
    )
    with open(PARENT_DIR / Path(f"models/doc_topic_dist.pkl"), "wb") as file_model:
        pickle.dump(doc_topic_dist, file_model, pickle.HIGHEST_PROTOCOL)

doc_dist = doc_topic_dist.iloc[0]

top_n = 10
distances = doc_topic_dist.apply(lambda x: jensenshannon(x, doc_dist), axis=1)
k_nearest = distances[distances != 0].nsmallest(n=top_n).index
k_distances = distances[distances != 0].nsmallest(n=top_n)

# Example query
three_musketeers_summary = """
First published in 1844, The Three Musketeers is the most famous of Alexandre Dumas' historical novels and one of the most popular adventure novels ever written.
Dumas' swashbuckling epic chronicles the adventures of d'Artagnan, a brash young man from the countryside who journeys to Paris in 1625 hoping to become a musketeer and guard to King Louis XIII. Before long, he finds treachery and court intrigue,and also three boon companions, the daring swordsmen Athos, Porthos, and Aramis. Together, the four strive heroically to defend the honor of their queen against the powerful Cardinal Richelieu and the seductive spy Milady.
"""

tasks_vectorized = vectorizer.transform([three_musketeers_summary])
tasks_topic_dist = lda.transform(tasks_vectorized)[0]
distances = doc_topic_dist.apply(lambda x: jensenshannon(x, tasks_topic_dist), axis=1)
k_nearest = distances[distances != 0].nsmallest(n=top_n).index
k_distances = distances[distances != 0].nsmallest(n=top_n)
print(f"The three musketeers similar books top {top_n}")
print(k_nearest)
