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
from similarbooks.main.utils import query_data
from som.utils import model_dict

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
    if search_form.validate_on_submit():
        books = query_data(
            BOOK_QUERY,
            {"title_contains": search_form.title.data, "summary_exists": True},
        )
    return render_template("home.html", books=books, search_form=search_form)


@main.route("/book/<sha>/")
@cache.cached(timeout=60)
def detailed_book(sha):
    book = query_data(
        DETAILED_BOOK_QUERY,
        {"sha": sha},
    )
    if len(book) > 0:
        book = book[0]  # Unlist the book
        som = model_dict["websom"]
        clean_book_id = book["node"]["book_id"]
        bmu_nodes = som.labels.get(clean_book_id)
        matched_indices = np.any(
            np.all(bmu_nodes == som.bmus[:, None, :], axis=2), axis=1
        )
        matched_list = list(pd.Series(som.labels.keys())[matched_indices])
        prefix_matched_list = [
            match for match in matched_list if match != clean_book_id
        ]
        similar_books = query_data(
            BOOK_QUERY,
            {"book_id_in": prefix_matched_list, "summary_exists": True},
        )
        return render_template(
            "detailed.html",
            book=book,
            similar_books=similar_books,
            description=book.get("summary"),
            title=f"{book.get('title')} by {book.get('author')}",
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
