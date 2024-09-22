import requests
import numpy as np
import itertools
import plotly
import plotly.graph_objects as go
from app.similarbooks.config import Config
from app.similarbooks.main.constants import (
    GRAPHQL_ENDPOINT,
)
from utils import load_file, get_bmus
import pandas as pd

# lat and lon for german states
# Source: https://github.com/isellsoap/deutschlandGeoJSON/tree/main

UMATRIX_STR = "umatrix"
PRICE_MATRIX_STR = "price_matrix"
RENT_PRICE_MATRIX_STR = "rent_price_matrix"
PRICE_PER_SQUARE_METER_STR = "price_per_square_meter"
RENT_PRICE_PER_SQUARE_METER_STR = "rent_price_per_square_meter"
PRICE_PER_RENT_PRICE = "price_per_rent_price"
NODE_COUNT = "node_count"
CASHFLOW = "cashflow"
TOTAL_PRICE = "total_price"
MAINTENANCE_PRICE = "maintenance_price"
UNITS = {
    "square_meter": "m²",
    "energy_consumption": "kWh/(m²·a)",
    "currency": "€",
}
UNITS.update(
    {
        PRICE_MATRIX_STR: UNITS["currency"],
        RENT_PRICE_MATRIX_STR: UNITS["currency"],
        PRICE_PER_SQUARE_METER_STR: f'{UNITS["currency"]}/{UNITS["square_meter"]}',
        RENT_PRICE_PER_SQUARE_METER_STR: f'{UNITS["currency"]}/{UNITS["square_meter"]}',
        CASHFLOW: UNITS["currency"],
        TOTAL_PRICE: UNITS["currency"],
        MAINTENANCE_PRICE: UNITS["currency"],
    }
)

DECIMAL_PRECISION = {
    PRICE_MATRIX_STR: 2,
    RENT_PRICE_MATRIX_STR: 2,
    PRICE_PER_SQUARE_METER_STR: 2,
    RENT_PRICE_PER_SQUARE_METER_STR: 2,
    CASHFLOW: 2,
    TOTAL_PRICE: 2,
    MAINTENANCE_PRICE: 2,
    UMATRIX_STR: 4,
    "energy_consumption": 2,
    "square_meter": 2,
    "lat": 4,
    "lon": 4,
}


def som_plot(
    data,
    dimname=UMATRIX_STR,
    colorscale="portland",
    reversescale=False,
    area_points=None,
):
    feature_title = f"{dimname} in {UNITS.get(dimname, '')}"
    fig = go.Figure(
        go.Contour(
            z=data[dimname],
            contours_coloring="heatmap",
            colorscale=colorscale,
            colorbar={"title": feature_title, "titleside": "right"},
            connectgaps=False,
            showscale=True,
            showlegend=False,
            hovertemplate="{0}: %{{z:.{1}f}} {2}<extra></extra>".format(
                dimname, DECIMAL_PRECISION.get(dimname, 0), UNITS.get(dimname, "")
            ),
            reversescale=reversescale,
        )
    )

    if area_points:
        # Add scatter plot for area_points
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in area_points],
                y=[p[1] for p in area_points],
                mode="markers",
                marker=dict(color="black", size=10),
                name="Points",
            )
        )

    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        font_color="rgba(255, 255, 255, 1)",
    )
    return fig


def get_node_number(som, coordinates):
    return som._n_columns * coordinates["y"] + coordinates["x"] + 1


def add_marker(fig, coordinates):
    fig.add_trace(
        go.Scatter(
            x=[point[0] for point in coordinates["points"]],
            y=[point[1] for point in coordinates["points"]],
            mode="markers",
            marker_symbol="x-thin",
            customdata=coordinates["z"],
            marker=dict(
                size=9, color="rgba(255, 0, 0, 0)", line_color="white", line_width=4
            ),
            hovertemplate="{0}: %{{customdata:.{1}f}} {2}<extra></extra>".format(
                coordinates["dimname"],
                DECIMAL_PRECISION.get(coordinates["dimname"], 0),
                UNITS.get(coordinates["dimname"], ""),
            ),
        )
    )
    return fig


def plot2json(fig):
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


ATTRIBUTE_QUERY = """
{{
  all_appartments (filters: {0}) {{
    edges {{
      node {{
        immo_id,
        rent_price,
        price,
        square_meter,
        location,
        maintenance_price,
        year_of_construction,
        rooms,
        lat,
        lon
      }}
    }}
  }}
}}""".strip()

ATTRIBUTE_COLUMN_NAMES = {
    "immo_id": str,
    "price": float,
    "rent_price": float,
    "square_meter": float,
    "year_of_construction": int,
    "location": str,
    "maintenance_price": float,
    "rooms": float,
    "lat": float,
    "lon": float,
}


def query(model, coordinates):
    sha_list = [
        model.labels[(np.array(point) == model.bmus).all(axis=1)]
        for point in coordinates["points"]
    ]
    sha_list = list(itertools.chain(*sha_list))
    print(f"Got sha list with length {len(sha_list)}")

    query_string = "{{immo_id_in: {0}}}".format(sha_list)

    print("Getting data ...")
    response = requests.post(
        url=GRAPHQL_ENDPOINT,
        json={"query": ATTRIBUTE_QUERY.format(query_string).replace("'", '"')},
        headers={"X-RapidAPI-Proxy-Secret": Config.SECRET_KEY},
    ).json()
    appartments = response["data"]["all_appartments"]["edges"]
    plot_data = {column_name: [] for column_name in ATTRIBUTE_COLUMN_NAMES}
    for appartment in appartments:
        for attribute, attribute_type in ATTRIBUTE_COLUMN_NAMES.items():
            plot_data[attribute].append(appartment["node"][attribute])
    df = pd.DataFrame(plot_data)
    df = df.set_index("immo_id")
    return df


# TODO: Add model tests so that they make sense
def main():
    clipped_values = {
        "lat": 100,
        "lon": 100,
        "square_meter": 300,
        "rooms": 20,
        "age": 400,
    }

    points = []
    latc, lonc = 52.51601397029215, 13.403959702821902
    for sq in range(30, 100):
        for yc in range(2019, 2020):
            flat_dict = {
                "immo_id": "2dfmv55",
                "lat": latc,
                "lon": lonc,
                "square_meter": sq,
                "rooms": 3,
                "year_of_construction": f"{yc}",
            }
            apartment_som, bmu_nodes = get_bmus("all_appartments", flat_dict)
            points.append((bmu_nodes[0][0], bmu_nodes[0][1]))

    apartment_scaler = model_dict["all_appartments"]["lat_lon_sq_bj_ro"]["scaler"]
    # go.Figure(get_cache("SOM_PLOTS")[get_cache("DIMNAME")])
    SOM_MATRIX = {
        dim_name: np.clip(
            apartment_scaler.unscale_matrix(
                {dim_name: apartment_som.codebook[:, :, idx]}, colname=dim_name
            ),
            None,
            clipped_values[dim_name],
        )
        for idx, dim_name in enumerate(["lat", "lon", "square_meter", "rooms", "age"])
    }
    SOM_MATRIX[UMATRIX_STR] = np.clip(apartment_som.umatrix, None, 0.1)

    umatrix = som_plot(SOM_MATRIX, UMATRIX_STR, area_points=points)
    lat = som_plot(SOM_MATRIX, "lat", area_points=points)
    lon = som_plot(SOM_MATRIX, "lon", area_points=points)
    sq = som_plot(SOM_MATRIX, "square_meter", area_points=points)
    rooms = som_plot(SOM_MATRIX, "rooms", area_points=points)
    age = som_plot(SOM_MATRIX, "age", area_points=points)

    umatrix.show()
    lat.show()
    lon.show()
    sq.show()
    rooms.show()
    age.show()

    # coords = {
    #     "dimname": UMATRIX_STR,
    #     "points": [[x, y]],
    # }
    # coords["z"] = [
    #     SOM_MATRIX[coords["dimname"]][point[1]][point[0]] for point in coords["points"]
    # ]
    # add_marker(umatrix, coords).show()

    # coords = {
    #     "dimname": PRICE_PER_SQUARE_METER_STR,
    #     "points": [[x, y]],
    # }
    # coords["z"] = [
    #     SOM_MATRIX[coords["dimname"]][point[1]][point[0]] for point in coords["points"]
    # ]
    # add_marker(p_sq, coords).show()

    # df = query(apartment_som, coords)
    # df["price_per_square_meter"] = df["price"] / df["square_meter"]
    # df["rent_per_square_meter"] = df["rent_price"] / df["square_meter"]
    # mean_price_per_square_meter = df["price_per_square_meter"].mean(skipna=True)
    # mean_rent_per_square_meter = df["rent_per_square_meter"].mean(skipna=True)
    # mean_price = df["price"].mean(skipna=True)
    # mean_square_meter = df["square_meter"].mean(skipna=True)
    # print(df)
    # print(mean_price_per_square_meter)
    # print(mean_rent_per_square_meter)
    # df.to_csv("/home/vkreschenski/Documents/Privat/Freelancer/similarbooks/som/df.csv")
    # som_plot(SOM_MATRIX, "rooms").show()
    # som_plot(SOM_MATRIX, "lat").show()
    # som_plot(SOM_MATRIX, "lon").show()
    # som_plot(SOM_MATRIX, "age").show()

    # apartment_som.view_umatrix()
    # apartment_som.view_component_planes()


if __name__ == "__main__":
    main()
