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
from similarbooks.main.utils import get_data_from_url, get_detailed_data
from som.utils import model_dict, get_coordinates, get_price_per_square_meter

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

    landing_form = LandingSearchForm()
    if landing_form.validate_on_submit():
        return redirect(url_for(landing_form.category.data, datemi=MIN_DATE_DISPLAY))

    form = PropertyForm()
    estimate = {
        "estimates": {
            "rent": 0.0,
            "price": 0.0,
            "similar_properties": [],
        },
        "location": {"lat": None, "lon": None},
    }
    if form.validate_on_submit():
        data = {
            "street": form.street.data,
            "postcode": form.postcode.data,
            "square_meters": form.square_meters.data,
            "rooms": form.rooms.data,
            "year_of_construction": form.year_of_construction.data,
            "typ": form.typ.data,
        }
        estimate = requests.post(
            url=request.host_url + "estimate",
            json=data,
            headers={"X-RapidAPI-Proxy-Secret": Config.EVAL_API_SECRET_KEY},
        ).json()
        # Return JSON response if it's an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(estimate)
    return render_template(
        "index.html",
        form=form,
        landing_form=landing_form,
        estimate=estimate,
        version=VERSION,
    )


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
