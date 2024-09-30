import sys
import requests
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import pickle
from pathlib import Path
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from dash import dash_table
from som.utils import parse_gutenberg_info, query_debug_display

PARENT_DIR = Path(__file__).resolve().parent

sys.modules["Scaler"] = Scaler


# Function to create the SOM plot
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


# Dash app setup
app = dash.Dash(__name__)

# Global variables for the SOM model
som = None
matched_list = None


# Main function to load the model and prepare the data
def load_model():
    global som, matched_list

    with open(PARENT_DIR / Path(f"models/websom.pkl"), "rb") as file_model:
        som = pickle.load(file_model)

    SOM_MATRIX = {}
    SOM_MATRIX["umatrix"] = som.umatrix
    return som_plot(SOM_MATRIX, "umatrix")


# Dash layout
app.layout = html.Div(
    [
        dcc.Graph(
            id="som-plot",
            figure=load_model(),  # Initialize the plot with the loaded model
            config={"displayModeBar": False},
        ),
        html.Div(id="hover-data"),  # Div to display matched_list based on hover
    ]
)


# Dash callback to capture hover data and update matched_list
@app.callback(Output("hover-data", "children"), [Input("som-plot", "hoverData")])
def display_hover_data(hoverData):
    if hoverData and som:
        # Get x and y coordinates from hover event
        x = int(hoverData["points"][0]["x"])
        y = int(hoverData["points"][0]["y"])

        # Update bmu_nodes based on hovered x, y values
        bmu_nodes = np.array([np.array([x, y])])

        # Find matched indices in the SOM based on bmu_nodes
        matched_indices = np.any(
            np.all(bmu_nodes == som.bmus[:, None, :], axis=2), axis=1
        )
        matched_list = list(pd.Series(som.labels.keys())[matched_indices])
        metadata = query_debug_display(matched_list)
        metadata_df = pd.json_normalize(metadata)

        # Return a Dash DataTable with the metadata
        return dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in metadata_df.columns],
            data=metadata_df.to_dict("records"),
            style_table={"overflowX": "auto"},  # Allow horizontal scrolling
            style_cell={
                "textAlign": "left",
                "padding": "5px",
                "whiteSpace": "normal",  # Allow wrapping of text
            },
            style_header={"backgroundColor": "lightgrey", "fontWeight": "bold"},
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "lightblue",
                },  # Stripe pattern
            ],
        )

    return "Hover over the plot to see the matched list."


# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True)
