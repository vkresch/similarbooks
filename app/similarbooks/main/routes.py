import datetime
from app.similarbooks.main.common import cache
from app.similarbooks.main.utils import get_param
from urllib.parse import urlparse
from urllib.parse import parse_qs
import requests
import hashlib
import logging
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
    MIN_SUMMARY_LENGTH,
)
from similarbooks.config import Config
from similarbooks.main.utils import (
    query_data,
    extract_and_add_params,
    get_similar_books,
)

VERSION = f"v{Config.VERSION_MAJOR}.{Config.VERSION_MINOR}.{Config.VERSION_PATCH}"

DAY_IN_SECONDS = 24 * 60 * 60

main = Blueprint("main", __name__)


@main.route("/ping")
def ping():
    return {"message": "alive"}


def extract_distinct_books(books, ignore_title=None):
    # Dictionary to store unique titles with the highest ratings_count
    unique_books = {}

    # Iterate through the list
    for book in books:
        title = book["node"]["title"]
        ratings_count = book["node"]["ratings_count"]

        if title is None or title == ignore_title:
            continue

        title = title.strip()

        # Add to unique_books if title is not in dictionary yet
        if title not in unique_books:
            unique_books[title] = book
        # If ratings_count is not None, compare and update if higher
        elif ratings_count is not None:
            existing_ratings = unique_books[title]["node"]["ratings_count"]
            # Update if the existing ratings_count is None or current ratings_count is higher
            if existing_ratings is None or ratings_count > existing_ratings:
                unique_books[title] = book

    # Convert the result back to a list
    result = list(unique_books.values())
    return result


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
            {
                "language": "English",
                "summary_length_gte": MIN_SUMMARY_LENGTH,
                "title_contains": query,
            },
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
        image_file = url_for("static", filename=f"covers/{sha}.png")
        matched_list = get_similar_books(
            [book["node"].get("bmu_col"), book["node"].get("bmu_row")], sha
        )
        similar_books = query_data(
            BOOK_QUERY,
            {
                "sha_in": matched_list,
                "language": "English",
                "summary_length_gte": MIN_SUMMARY_LENGTH,
            },
        )
        unique_similar_books = extract_distinct_books(
            similar_books, ignore_title=book["node"].get("title")
        )
        kindle_link = extract_and_add_params(book["node"].get("kindle_link"))
        amazon_link = extract_and_add_params(book["node"].get("amazon_link"))
        return render_template(
            "detailed.html",
            book=book,
            amazon_link=amazon_link,
            kindle_link=kindle_link,
            similar_books=unique_similar_books,
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
