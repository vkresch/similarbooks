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
from similarbooks.config import Config
from similarbooks.main.utils import query_data

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
    filter_dict = {}
    if search_form.validate_on_submit():
        filter_dict = {"title_contains": search_form.title.data}
    books = query_data(
        filter_dict,
        1,
        "date",
        "all_books",
    )
    return render_template("home.html", books=books, search_form=search_form)


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
    return render_template("datenschutz.html", title="Datenschutz")


@main.route("/legal")
@cache.cached(timeout=60)
def legal():
    return render_template("legal.html", title="Legal")
