import os
import logging
import somoclu
import numpy as np
import datetime
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from Scaler import Scaler
from time import perf_counter
from pathlib import Path
import pickle
from tqdm import tqdm  # For progress bar
from som.utils import (
    encode_kaski,
    preprocess_text,
    load_documents_dict,
    load_documents_graphql,
    get_hit_histogram,
    draw_barchart,
    query_training_data,
)
from som.train_lda import train_lda, train_gensim_lda
import matplotlib.pyplot as plt


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent

# doc_topic_dist = train_lda()
doc_topic_dist = train_gensim_lda(
    topic_n=100,
    use_cache_lda_summaries_dict=False,
    use_cache_lda_corpus=False,
    use_cache_lda=False,
    use_cache_doc_topic_dist=False,
)

logging.info(f"Data shape: {doc_topic_dist.shape}")
som = somoclu.Somoclu(
    200,
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
    data=doc_topic_dist.to_numpy(dtype="float32"),
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

som.labels = dict(zip(doc_topic_dist.index, som.bmus))

with open(PARENT_DIR / Path(f"models/lda_websom.pkl"), "wb") as file_model:
    som.name = f"lda_websom"
    pickle.dump(som, file_model, pickle.HIGHEST_PROTOCOL)
