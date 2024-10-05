import numpy as np
import pandas as pd
import datetime
from app.similarbooks.main.common import cache
from app.similarbooks.main.utils import get_param
from urllib.parse import urlparse
from urllib.parse import parse_qs
import requests
import hashlib
import json
import plotly
import plotly.graph_objects as go
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
from similarbooks.main.utils import query_data, extract_and_add_params
from som.utils import model_dict, get_similar_books_lda, get_top_bmus

VERSION = f"v{Config.VERSION_MAJOR}.{Config.VERSION_MINOR}.{Config.VERSION_PATCH}"

DAY_IN_SECONDS = 24 * 60 * 60

main = Blueprint("main", __name__)


@main.route("/ping")
def ping():
    return {"message": "alive"}


def som_plot(
    data,
    title,
    dimname="umatrix",
    colorscale="portland",
    reversescale=False,
    area_points=None,
    highlight_point=None,  # Expects a list or array like [[X, Y]]
):
    feature_title = f"{dimname}"
    fig = go.Figure(
        go.Contour(
            z=data[dimname],
            contours_coloring="heatmap",
            colorscale=colorscale,
            colorbar=dict(
                title=feature_title,  # Title of the colorbar
                titleside="top",  # Position title above the colorbar
                len=0.5,  # Length of the colorbar
                thickness=20,  # Thickness of the colorbar
                x=0.5,  # Center the colorbar horizontally
                y=-0.1,  # Position the colorbar just below the plot
                xanchor="center",  # Anchor the colorbar to the center of x
                yanchor="top",  # Anchor the colorbar to the top of y
            ),
            connectgaps=False,
            showscale=False,
            showlegend=False,
            reversescale=reversescale,
            hoverinfo="none",  # Disable hover popup for the contour
        )
    )

    if highlight_point is not None:
        # Ensure highlight_point is a list or convert it from numpy array
        highlight_point = np.array(highlight_point).tolist()

        # Check if highlight_point is in the format [[X, Y]]
        if len(highlight_point) == 1 and len(highlight_point[0]) == 2:
            x_coord = highlight_point[0][0]
            y_coord = highlight_point[0][1]

            # Add a single scatter point for the highlight_point (X, Y)
            fig.add_trace(
                go.Scatter(
                    x=[x_coord],  # X coordinate
                    y=[y_coord],  # Y coordinate
                    mode="markers+text",  # Show marker with text
                    marker=dict(color="red", size=12, symbol="circle"),
                    textposition="top right",  # Position the label
                    name="Highlight Point",
                    hoverinfo="none",  # Disable hover popup for highlight point
                )
            )

    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=40),  # Adjust bottom margin for colorbar
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        font_color="rgba(255, 255, 255, 1)",
        xaxis=dict(showticklabels=False),  # Remove x-axis numbers
        yaxis=dict(showticklabels=False),  # Remove y-axis numbers
    )

    return fig


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
    unique_books = []
    searched = False
    query = request.args.get("query")
    if query:
        searched = True
        books = query_data(
            BOOK_QUERY,
            {
                "title_contains": query,
                "language": "English",
                "summary_length_gte": MIN_SUMMARY_LENGTH,
            },
        )
        unique_books = extract_distinct_books(books)
    return render_template(
        "home.html", searched=searched, books=unique_books, search_form=search_form
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
            [
                (book["node"].get("title") or "")
                + " "
                + (book["node"].get("summary") or "")
            ]
        )
        tasks_topic_dist = model_dict["lda"].transform(tasks_vectorized)[0]
        active_map = som.get_surface_state(data=np.array([tasks_topic_dist]))
        bmu_nodes = get_top_bmus(som, active_map, top_n=1)
        # bmu_nodes = som.labels.get(book_id)
        matched_indices = np.any(
            np.all(bmu_nodes == som.bmus[:, None, :], axis=2), axis=1
        )
        matched_list = list(pd.Series(som.labels.keys())[matched_indices])
        SOM_MATRIX = {}
        SOM_MATRIX["similarity"] = som.umatrix
        fig = som_plot(
            SOM_MATRIX,
            book["node"].get("title"),
            "similarity",
            highlight_point=bmu_nodes,
        )
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        # matched_list = get_similar_books_lda(
        #     (book["node"].get("title") or "")
        #     + " "
        #     + (book["node"].get("summary") or "")
        # )
        prefix_matched_list = [match for match in matched_list if match != book_id]
        similar_books = query_data(
            BOOK_QUERY,
            {
                "book_id_in": prefix_matched_list,
                "language": "English",
                "summary_length_gte": MIN_SUMMARY_LENGTH,
            },
        )
        unique_similar_books = extract_distinct_books(
            similar_books, ignore_title=book["node"].get("title")
        )
        amazon_link = extract_and_add_params(book["node"].get("amazon_link"))
        return render_template(
            "detailed.html",
            book=book,
            amazon_link=amazon_link,
            similar_books=unique_similar_books,
            description=book.get("node").get("summary"),
            image_file=image_file,
            title=f"{book.get('node').get('title')} by {book.get('node').get('author')}",
            graphJSON=graphJSON,
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
