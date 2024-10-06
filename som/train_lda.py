import os
import logging
import numpy as np
import datetime
import pandas as pd
from gensim.corpora import Dictionary, MmCorpus
from gensim.models import LdaMulticore
from gensim.utils import simple_preprocess
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
    load_documents_graphql,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARENT_DIR = Path(__file__).resolve().parent


def train_lda(
    topic_n=100,
    use_cache_lda_summaries_dict=True,
    use_cache_lda_corpus=True,
    use_cache_lda=True,
    use_cache_doc_topic_dist=True,
):
    if use_cache_lda_summaries_dict and os.path.exists(
        PARENT_DIR / Path(f"models/lda_summaries_dict.pkl")
    ):
        logging.info(f"Loading cached summaries dict ...")
        with open(
            PARENT_DIR / Path(f"models/lda_summaries_dict.pkl"), "rb"
        ) as file_model:
            summaries_dict = pickle.load(file_model)
    else:
        logging.info(f"Querying new summaries dict ...")
        # documents = load_documents_graphql(PARENT_DIR / "data")
        summaries_dict = query_training_data(limited=False)
        # summaries_dict.extend(documents)

        with open(
            PARENT_DIR / Path(f"models/lda_summaries_dict.pkl"), "wb"
        ) as file_model:
            pickle.dump(summaries_dict, file_model, pickle.HIGHEST_PROTOCOL)

    if use_cache_lda_corpus and os.path.exists(
        PARENT_DIR / Path(f"models/lda_dtm.pkl")
    ):
        logging.info(f"Loading already vectorizer ...")
        with open(PARENT_DIR / Path(f"models/lda_vectorizer.pkl"), "rb") as file_model:
            vectorizer = pickle.load(file_model)
        logging.info(f"Loading already encoded DTM ...")
        with open(PARENT_DIR / Path(f"models/lda_dtm.pkl"), "rb") as file_model:
            dtm = pickle.load(file_model)
    else:
        logging.info(f"Preparing summaries ...")
        summaries = [
            (item.get("node").get("title") or "")
            + " "
            + item.get("node").get("summary")
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

    if use_cache_lda and os.path.exists(PARENT_DIR / Path(f"models/lda.pkl")):
        logging.info(f"Loading already encoded LDA model ...")
        with open(PARENT_DIR / Path(f"models/lda.pkl"), "rb") as file_model:
            lda = pickle.load(file_model)
    else:
        logging.info(f"Training LDA model ...")
        lda = LatentDirichletAllocation(
            n_components=topic_n,
            random_state=42,
            n_jobs=os.cpu_count(),
            verbose=1,
        )
        lda.fit(dtm)

        with open(PARENT_DIR / Path(f"models/lda.pkl"), "wb") as file_model:
            pickle.dump(lda, file_model, pickle.HIGHEST_PROTOCOL)

    if use_cache_doc_topic_dist and os.path.exists(
        PARENT_DIR / Path(f"models/doc_topic_dist.pkl")
    ):
        logging.info(f"Loading document distance data frame ...")
        with open(PARENT_DIR / Path(f"models/doc_topic_dist.pkl"), "rb") as file_model:
            doc_topic_dist = pickle.load(file_model)
    else:
        logging.info(f"Generating doc_topic_dist ...")
        doc_topic_dist = pd.DataFrame(
            lda.transform(dtm),
            index=[item.get("node").get("sha") for item in summaries_dict],
        )
        with open(PARENT_DIR / Path(f"models/doc_topic_dist.pkl"), "wb") as file_model:
            pickle.dump(doc_topic_dist, file_model, pickle.HIGHEST_PROTOCOL)

    # Example query
    three_musketeers_summary = """
    First published in 1844, The Three Musketeers is the most famous of Alexandre Dumas' historical novels and one of the most popular adventure novels ever written.
    Dumas' swashbuckling epic chronicles the adventures of d'Artagnan, a brash young man from the countryside who journeys to Paris in 1625 hoping to become a musketeer and guard to King Louis XIII. Before long, he finds treachery and court intrigue,and also three boon companions, the daring swordsmen Athos, Porthos, and Aramis. Together, the four strive heroically to defend the honor of their queen against the powerful Cardinal Richelieu and the seductive spy Milady.
    """

    top_n = 10
    tasks_vectorized = vectorizer.transform([three_musketeers_summary])
    tasks_topic_dist = lda.transform(tasks_vectorized)[0]
    distances = doc_topic_dist.apply(
        lambda x: jensenshannon(x, tasks_topic_dist), axis=1
    )
    k_nearest = distances[distances != 0].nsmallest(n=top_n).index
    k_distances = distances[distances != 0].nsmallest(n=top_n)
    print(f"The three musketeers similar books top {top_n}")
    print(k_nearest)

    return doc_topic_dist


# Streamed and memory-efficient tokenization function
def tokenize_documents(documents):
    for doc in documents:
        # Tokenize and yield one document at a time
        yield simple_preprocess(doc)


# Stream documents to create the dictionary and corpus
def build_dictionary_and_corpus(documents, dictionary_path, corpus_path):
    # Create a dictionary without loading everything into memory
    dictionary = Dictionary(tokenize_documents(documents))
    dictionary.filter_extremes(no_below=2, no_above=0.85)

    # Save the dictionary to disk
    with open(dictionary_path, "wb") as file_model:
        pickle.dump(dictionary, file_model, pickle.HIGHEST_PROTOCOL)

    # Memory-efficient corpus generation: stream and save directly to disk
    def generate_corpus():
        for doc in tokenize_documents(documents):
            yield dictionary.doc2bow(doc)

    # Save the corpus using MmCorpus (efficient sparse format on disk)
    MmCorpus.serialize(str(corpus_path), generate_corpus())


def train_gensim_lda(
    topic_n=100,
    use_cache_lda_summaries_dict=True,
    use_cache_lda_corpus=True,
    use_cache_lda=True,
    use_cache_doc_topic_dist=True,
):
    # Load or query document summaries
    if use_cache_lda_summaries_dict and os.path.exists(
        PARENT_DIR / Path(f"models/lda_summaries_dict.pkl")
    ):
        logging.info(f"Loading cached summaries dict ...")
        with open(
            PARENT_DIR / Path(f"models/lda_summaries_dict.pkl"), "rb"
        ) as file_model:
            summaries_dict = pickle.load(file_model)
    else:
        logging.info(f"Querying new summaries dict ...")
        # documents = load_documents_graphql(PARENT_DIR / "data")
        summaries_dict = query_training_data(limited=False)
        # summaries_dict.extend(documents)

        with open(
            PARENT_DIR / Path(f"models/lda_summaries_dict.pkl"), "wb"
        ) as file_model:
            pickle.dump(summaries_dict, file_model, pickle.HIGHEST_PROTOCOL)

    # Load or generate the Gensim corpus and dictionary
    if use_cache_lda_corpus and os.path.exists(
        PARENT_DIR / Path(f"models/lda_corpus.pkl")
    ):
        logging.info(f"Loading cached Gensim corpus ...")
        with open(PARENT_DIR / Path(f"models/lda_corpus.pkl"), "rb") as file_model:
            corpus = pickle.load(file_model)
    else:
        if not os.path.exists(
            PARENT_DIR / Path(f"models/lda_corpus.mm")
        ):
            logging.info(f"Preparing summaries ...")
            summaries = [
                (item.get("node").get("title") or "")
                + " "
                + item.get("node").get("summary")
                for item in summaries_dict
            ]

            # Build dictionary and corpus using memory-efficient method
            build_dictionary_and_corpus(
                summaries,
                PARENT_DIR / Path(f"models/lda_dictionary.pkl"),
                PARENT_DIR / Path(f"models/lda_corpus.mm"),
            )

        # Load the generated corpus for further processing
        corpus = MmCorpus(str(PARENT_DIR / Path(f"models/lda_corpus.mm")))

        with open(PARENT_DIR / Path(f"models/lda_corpus.pkl"), "wb") as file_model:
            pickle.dump(corpus, file_model, pickle.HIGHEST_PROTOCOL)

    # Load or train the LDA model
    if use_cache_lda and os.path.exists(PARENT_DIR / Path(f"models/lda_gensim.pkl")):
        logging.info(f"Loading cached Gensim LDA model ...")
        with open(PARENT_DIR / Path(f"models/lda_gensim.pkl"), "rb") as file_model:
            lda = pickle.load(file_model)
    else:
        if os.path.exists(
            PARENT_DIR / Path(f"models/lda_dictionary.pkl")
        ):
            logging.info(f"Loading dictionary ...")
            with open(PARENT_DIR / Path(f"models/lda_dictionary.pkl"), "rb") as file_model:
                dictionary = pickle.load(file_model)
        
        logging.info(f"Training Gensim LDA model ...")
        lda = LdaMulticore(
            corpus=corpus,
            id2word=dictionary,
            num_topics=topic_n,
            random_state=42,
            passes=10,
            workers=os.cpu_count(),  # Use all available cores
        )

        with open(PARENT_DIR / Path(f"models/lda_gensim.pkl"), "wb") as file_model:
            pickle.dump(lda, file_model, pickle.HIGHEST_PROTOCOL)

    # Generate document-topic distributions
    if use_cache_doc_topic_dist and os.path.exists(
        PARENT_DIR / Path(f"models/doc_topic_dist_gensim.pkl")
    ):
        logging.info(f"Loading document distance data frame ...")
        with open(
            PARENT_DIR / Path(f"models/doc_topic_dist_gensim.pkl"), "rb"
        ) as file_model:
            doc_topic_dist = pickle.load(file_model)
    else:
        logging.info(f"Generating document-topic distributions ...")
        doc_topic_dist = pd.DataFrame(
            {
                i: dict(lda.get_document_topics(corpus[i], minimum_probability=0))
                for i in range(len(corpus))
            }
        ).T.fillna(
            0
        )  # Ensure NaNs are replaced with zeros

        # Set the index to book_id
        doc_topic_dist.index = [item.get("node").get("sha") for item in summaries_dict]

        with open(
            PARENT_DIR / Path(f"models/doc_topic_dist_gensim.pkl"), "wb"
        ) as file_model:
            pickle.dump(doc_topic_dist, file_model, pickle.HIGHEST_PROTOCOL)

    # Example query
    three_musketeers_summary = """
    First published in 1844, The Three Musketeers is the most famous of Alexandre Dumas' historical novels and one of the most popular adventure novels ever written.
    Dumas' swashbuckling epic chronicles the adventures of d'Artagnan, a brash young man from the countryside who journeys to Paris in 1625 hoping to become a musketeer and guard to King Louis XIII. Before long, he finds treachery and court intrigue,and also three boon companions, the daring swordsmen Athos, Porthos, and Aramis. Together, the four strive heroically to defend the honor of their queen against the powerful Cardinal Richelieu and the seductive spy Milady.
    """

    top_n = 10
    tasks_vectorized = dictionary.doc2bow(three_musketeers_summary.split())
    tasks_topic_dist = dict(
        lda.get_document_topics(tasks_vectorized, minimum_probability=0)
    )
    distances = doc_topic_dist.apply(
        lambda x: jensenshannon(x, list(tasks_topic_dist.values())), axis=1
    )
    k_nearest = distances[distances != 0].nsmallest(n=top_n).index
    k_distances = distances[distances != 0].nsmallest(n=top_n)
    print(f"The three musketeers similar books top {top_n}")
    print(k_nearest)

    return doc_topic_dist
