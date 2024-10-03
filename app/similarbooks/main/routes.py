import numpy as np
import pandas as pd
import datetime
from app.similarbooks.main.common import cache
from app.similarbooks.main.utils import get_param
from urllib.parse import urlparse
from urllib.parse import parse_qs
import requests
import hashlib
from flask import (
    render_template,
    request,
    flash,
    Blueprint,
    url_for,
    redirect,
    jsonify,
)
from similarbooks.main.forms import (
    LandingSearchForm,
)
from similarbooks.main.constants import (
    BOOK_QUERY,
    DETAILED_BOOK_QUERY,
)
from similarbooks.config import Config
from similarbooks.main.utils import query_data, extract_and_add_params
from som.utils import model_dict, get_similar_books_lda, get_top_bmus

VERSION = f"v{Config.VERSION_MAJOR}.{Config.VERSION_MINOR}.{Config.VERSION_PATCH}"

DAY_IN_SECONDS = 24 * 60 * 60

main = Blueprint("main", __name__)


@main.route("/ping")
def ping():
    return {"message": "alive"}


@main.route("/home", methods=["POST", "GET"])
@main.route("/", methods=["POST", "GET"])
def index():
    search_form = LandingSearchForm()
    books = []
    searched = False
    query = request.args.get("query")
    if query:
        searched = True
        books = query_data(
            BOOK_QUERY,
            {"title_contains": query, "language": "English"},
        )
    return render_template(
        "home.html", searched=searched, books=books, search_form=search_form
    )


@main.route("/book/<sha>/")
@cache.cached(timeout=60)
def detailed_book(sha):
    book = query_data(
        DETAILED_BOOK_QUERY,
        {"sha": sha},
    )
    if len(book) > 0:
        book = book[0]  # Unlist the book
        som = model_dict["lda_websom"]
        book_id = book["node"]["book_id"]
        image_file = url_for("static", filename=f"covers/{sha}.png")
        tasks_vectorized = model_dict["vectorizer"].transform(
            [(book["node"].get("title") or "") + " " + (book["node"].get("summary") or "")]
        )
        tasks_topic_dist = model_dict["lda"].transform(tasks_vectorized)[0]
        active_map = som.get_surface_state(data=np.array([tasks_topic_dist]))
        bmu_nodes = get_top_bmus(som, active_map, top_n=1)
        # bmu_nodes_lookup = som.labels.get(book_id)
        matched_indices = np.any(
            np.all(bmu_nodes == som.bmus[:, None, :], axis=2), axis=1
        )
        matched_list = list(pd.Series(som.labels.keys())[matched_indices])
        # matched_list = get_similar_books_lda(
        #     book["node"].get("title") + " " + book["node"].get("summary")
        # )
        prefix_matched_list = [match for match in matched_list if match != book_id]
        similar_books = query_data(
            BOOK_QUERY,
            {"book_id_in": prefix_matched_list, "language": "English"},
        )
        amazon_link = extract_and_add_params(book["node"].get("amazon_link"))
        return render_template(
            "detailed.html",
            book=book,
            amazon_link=amazon_link,
            similar_books=similar_books,
            description=book.get("node").get("summary"),
            image_file=image_file,
            title=f"{book.get('node').get('title')} by {book.get('node').get('author')}",
        )
    return render_template("not_found.html")


@main.route("/about")
@cache.cached(timeout=60)
def about():
    return render_template("about.html", title="About")


@main.route("/impressum")
@cache.cached(timeout=60)
def impressum():
    return render_template("impressum.html", title="Impressum")


@main.route("/datenschutz")
@cache.cached(timeout=60)
def datenschutz():
    return render_template("datenschutz.html", title="Data Privacy")


@main.route("/legal")
@cache.cached(timeout=60)
def legal():
    return render_template("legal.html", title="Legal")
