import requests
import numpy as np
import plotly.graph_objects as go
from utils import load_file, model_dict, get_price_per_square_meter
import pandas as pd
import pickle
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parent


def som_plot(
    data,
    dimname="umatrix",
    colorscale="portland",
    reversescale=False,
    area_points=None,
):
    feature_title = f"{dimname}"
    fig = go.Figure(
        go.Contour(
            z=data[dimname],
            contours_coloring="heatmap",
            colorscale=colorscale,
            colorbar={"title": feature_title, "titleside": "right"},
            connectgaps=False,
            showscale=True,
            showlegend=False,
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


# TODO: Add model tests so that they make sense
def main():
    with open(PARENT_DIR / Path(f"models/wordcategory.pkl"), "rb") as file_model:
        som = pickle.load(file_model)

    bmu_nodes = np.array([np.array([20, 39])])
    matched_indices = np.any(np.all(bmu_nodes == som.bmus[:, None, :], axis=2), axis=1)
    # print(som.labels)
    # print(matched_indices)
    matched_list = list(som.labels[matched_indices])
    print(matched_list)

    SOM_MATRIX = {}
    # SOM_MATRIX["umatrix"] = np.clip(som.umatrix, None, 0.1)
    SOM_MATRIX["umatrix"] = som.umatrix
    umatrix = som_plot(SOM_MATRIX, "umatrix")
    umatrix.show()


if __name__ == "__main__":
    main()
