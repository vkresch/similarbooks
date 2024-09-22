import datetime
from app.similarbooks.main.common import cache
from app.similarbooks.main.utils import get_param
from app.similarbooks.main.constants import (
    DEFAULT_INTEREST,
    DEFAULT_REPAYMENT,
    DEFAULT_EQUITY,
    MIN_DATE_DISPLAY,
)
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
    FeedbackForm,
    PropertyForm,
    LandingSearchForm,
)
from similarbooks.config import Config

VERSION = f"v{Config.VERSION_MAJOR}.{Config.VERSION_MINOR}.{Config.VERSION_PATCH}"

DAY_IN_SECONDS = 24 * 60 * 60

main = Blueprint("main", __name__)


@main.route("/ping")
def ping():
    return {"message": "alive"}


@main.route("/home", methods=["POST", "GET"])
@main.route("/", methods=["POST", "GET"])
def index():
    return render_template("home.html")


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
