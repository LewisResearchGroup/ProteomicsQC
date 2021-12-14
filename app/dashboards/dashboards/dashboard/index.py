import os
import sys
import pandas as pd
import numpy as np
from plotly.missing_ipywidgets import FigureWidget
import requests

import dash
import plotly
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

import plotly.express as px
import panel as pn

pn.extension("plotly")

import dash_table as dt
import dash_table

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_tabulator import DashTabulator

from lrg_omics.plotly import plotly_heatmap, plotly_bar, plotly_histogram, set_template
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import pdist, squareform

try:
    from .tools import list_to_dropdown_options
    from . import tools as T
except:
    from tools import list_to_dropdown_options
    import tools as T

set_template()


if __name__ == "__main__":
    app = dash.Dash(__name__)
    import proteins, quality_control, explorer
    from tools import (
        table_from_dataframe,
        get_projects,
        get_pipelines,
        get_protein_groups,
        get_qc_data,
        list_to_dropdown_options,
        get_protein_names,
    )

    import config as C
    import tools as T

    app.config.suppress_callback_exceptions = True
else:
    from django_plotly_dash import DjangoDash
    from . import proteins, quality_control, explorer

    from .tools import (
        table_from_dataframe,
        get_projects,
        get_pipelines,
        get_protein_groups,
        get_qc_data,
        list_to_dropdown_options,
        get_protein_names,
    )

    from . import config as C
    from . import tools as T

    app = DjangoDash(
        "dashboard",
        add_bootstrap_links=True,
        suppress_callback_exceptions=True,
        external_stylesheets=[],
    )

timeout = 360

protein_table_default_cols = []

layout = html.Div(
    [
        dcc.Loading(dcc.Store(id="store")),
        html.H1("Dashboard"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Button(
                            "Load projects and pipelines",
                            id="B_update",
                            className="btn",
                        ),
                        dcc.Dropdown(
                            id="project", options=get_projects(), value="lsarp"
                        ),
                    ]
                ),
                dbc.Col([dcc.Dropdown(id="pipeline", options=[], value=None)]),
                dbc.Col(
                    [
                        html.Div(
                            dcc.Dropdown(
                                id="data-range", options=C.data_range_options, value=300
                            ),
                            style={"display": "block"},
                        ),
                    ]
                ),
            ],
            style={"width": 300, "display": "inline-block"},
        ),
        dcc.Markdown("---"),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            dcc.Tabs(
                                id="tabs",
                                value="quality_control",
                                children=[
                                    dcc.Tab(
                                        id="tab-qc",
                                        label="Quality Control",
                                        value="quality_control",
                                    ),
                                    dcc.Tab(
                                        id="tab-explorer",
                                        label="Explorer",
                                        value="explorer",
                                    ),
                                    dcc.Tab(label="Proteins", value="proteins"),
                                ],
                            ),
                            dcc.Markdown("---"),
                            html.P(
                                [
                                    "Choose columns:",
                                    dcc.Dropdown(
                                        id="qc-table-columns",
                                        multi=True,
                                        options=list_to_dropdown_options(
                                            C.qc_columns_options
                                        ),
                                        placeholder="Select data columns",
                                        value=C.qc_columns_default,
                                    ),
                                ]
                            ),
                            html.Button(
                                "Load Data",
                                id="qc-update-table",
                                className="btn",
                            ),
                            dcc.Loading(
                                [
                                    html.Div(
                                        id="qc-table-div",
                                        children=[dt.DataTable(id="qc-table")],
                                        style={
                                            "margin-top": "1.5em",
                                            "minHeight": "400px",
                                        },
                                    )
                                ]
                            ),
                            # hack to turn off browser autocomplete
                            html.Script(
                                children='document.getElementById("qc-table-columns").getAttribute("autocomplete") = "off";'
                            ),
                            html.Div(id="tabs-content"),
                        ]
                    )
                )
            ]
        ),
        html.Div(id="selection-output"),
    ],
    style={"max-width": "90%", "display": "block", "margin": "auto"},
)

app.layout = layout

proteins.callbacks(app)
explorer.callbacks(app)


@app.callback(Output("tabs-content", "children"), [Input("tabs", "value")])
def render_content(tab):
    if tab == "proteins":
        return proteins.layout
    if tab == "quality_control":
        return quality_control.layout
    if tab == "explorer":
        return explorer.layout


@app.callback(Output("project", "options"), [Input("B_update", "n_clicks")])
def populate_projects(project):
    return get_projects()


@app.callback(Output("pipeline", "options"), [Input("project", "value")])
def populate_pipelines(project):
    _json = get_pipelines(project)
    if len(_json) == 0:
        return []
    else:
        output = [{"label": i["name"], "value": i["slug"]} for i in _json]
        return output


@app.callback(
    Output("qc-table-div", "children"),
    [Input("qc-update-table", "n_clicks")],
    [
        State("pipeline", "value"),
        State("project", "value"),
        State("qc-table-columns", "value"),
        State("data-range", "value"),
    ],
)
def refresh_qc_table(n_clicks, pipeline, project, optional_columns, data_range):
    if (project is None) or (pipeline is None):
        raise PreventUpdate
    columns = C.qc_columns_always + optional_columns
    data = get_qc_data(
        project=project, pipeline=pipeline, columns=columns, data_range=data_range
    )

    df = pd.DataFrame(data)

    if False:
        # Some code for testing purposes
        # blows up the dataframe for
        # testing performance and visualizations
        df = pd.concat([df] * 1000)
        df["RawFile"] = [fn + f".{i}" for i, fn in enumerate(df.RawFile)]
        df["Index"] = range(len(df))

    if "DateAcquired" in df.columns:
        df["DateAcquired"] = pd.to_datetime(df["DateAcquired"])
        df = df.replace("not detected", np.NaN)[C.qc_columns_always + optional_columns]
    return table_from_dataframe(df, id="qc-table", row_selectable="multi")


inputs = [Input("refresh-plots", "n_clicks")]
states = [
    State("qc-table", "selected_rows"),
    State("qc-table", "derived_virtual_indices"),
    State("x", "value"),
    State("qc-table", "data"),
    State("qc-table-columns", "value"),
]

plot_map = [
    {"title": "PSMs [%]", "plots": [{"y": "MS/MS Identified [%]", "label": "n_psm"}]},
    {
        "title": "Peptides / Protein Groups",
        "plots": [
            {"y": "N_peptides", "label": "n_peptides"},
            {"y": "N_protein_groups", "label": "n_proteins"},
        ],
    },
    {
        "title": "Oxidations [%]",
        "plots": [{"y": "Oxidations [%]", "label": "Oxidations [%]"}],
    },
    {
        "title": "Missed Cleavages [%]",
        "plots": [
            {"y": "N_missed_cleavages_eq_1 [%]", "label": "Missed Cleavages [%]"},
        ],
    },
    {
        "title": "Median fill times (ms)",
        "plots": [
            {"y": "MedianMs1FillTime(ms)", "label": "Median MS1 Fill Time"},
            {"y": "MedianMs2FillTime(ms)", "label": "Median MS2 Fill Time"},
        ],
    },
    {
        "title": "Total MS Scans",
        "plots": [
            {"y": "NumMs1Scans", "label": "# MS1 scans"},
            {"y": "NumMs2Scans", "label": "# MS2 scans"},
            {"y": "NumMs3Scans", "label": "# MS3 scans"},
        ],
    },
    {
        "title": "ESI Instability Flags",
        "plots": [{"y": "NumEsiInstabilityFlags", "label": "ESI Instability"}],
    },
]


# @lru_cache(maxsize=32)
@app.callback(
    Output("qc-figure", "figure"), Output("qc-figure", "config"), inputs, states
)
def plot_qc_figure(refresh, selected, ndxs, x, data, optional_columns):
    """Creates the bar-plot figure"""
    if (data is None) or (ndxs is None) or (len(ndxs) == 0):
        raise PreventUpdate

    if x is None:
        x = "RawFile"

    titles = [el["title"] for el in plot_map]

    df = pd.DataFrame(data)

    assert pd.value_counts(df.columns).max() == 1, pd.value_counts(df.columns)

    df["DateAcquired"] = pd.to_datetime(df["DateAcquired"])

    if ndxs is not None:
        df = df.reindex(ndxs)

    numeric_columns = df[optional_columns].head(1)._get_numeric_data().columns

    fig = make_subplots(
        cols=1,
        rows=len(numeric_columns),
        subplot_titles=numeric_columns,
        shared_xaxes=True,
        # vertical_spacing=0.05,
        print_grid=True,
    )

    for i, col in enumerate(numeric_columns):
        trace = go.Bar(
            x=df[x],
            y=df[col],
            name=col,
            text=None if x == "RawFile" else df["RawFile"],
        )
        fig.add_trace(trace, row=1 + i, col=1)

    fig.update_layout(hovermode="closest")

    fig.update_layout(
        height=200 + 250 * (i + 1),
        showlegend=False,
        margin=dict(l=50, r=10, b=200, t=50, pad=0),
    )

    marker_color = df["Use Downstream"].replace(
        {True: C.colors["use_downstream"], False: C.colors["dont_use_downstream"]}
    )
    marker_line_color = df["Flagged"].replace(
        {True: C.colors["flagged"], False: C.colors["not_flagged"]}
    )

    for ndx in selected:
        marker_color[ndx] = C.colors["selected"]

    fig.update_traces(
        marker_color=marker_color,
        marker_line_color=marker_line_color,
        marker_line_width=1,
        opacity=0.8,
    )

    fig.update_xaxes(matches="x")

    if x == "RawFile":
        fig.update_layout(
            xaxis5=dict(
                tickmode="array", tickvals=tuple(range(len(df))), ticktext=tuple(df[x])
            )
        )

    config = T.gen_figure_config(filename="QC-barplot")

    return fig, config


@app.callback(
    Output("qc-table", "selected_rows"),
    Input("qc-figure", "selectedData"),
    Input("qc-figure", "clickData"),
    Input("explorer-figure", "selectedData"),
    Input("explorer-figure", "clickData"),
    Input("qc-update-table", "n_clicks"),
    State("qc-table", "selected_rows"),
    State("qc-table", "derived_virtual_indices"),
)
def display_click_data(
    selectedData,
    clickData,
    explorerSelectedData,
    explorerClickData,
    table_refresh,
    selected_rows,
    virtual_ndxs,
):
    if (
        (selectedData is None)
        and (clickData is None)
        and (explorerSelectedData is None)
        and (explorerClickData is None)
    ):
        raise PreventUpdate

    changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]

    if changed_id == "qc-figure.selectedData":
        points = selectedData["points"]
        ndxs = [virtual_ndxs[p["pointIndex"]] for p in points]
        selected_rows.extend(ndxs)

    if changed_id == "qc-figure.clickData":
        ndx = clickData["points"][0]["pointIndex"]
        ndx = virtual_ndxs[ndx]
        if ndx in selected_rows:
            selected_rows.remove(ndx)
        else:
            selected_rows.append(ndx)

    if changed_id == "explorer-figure.clickData":
        ndx = explorerClickData["points"][0]["pointIndex"]
        ndx = virtual_ndxs[ndx]
        if ndx in selected_rows:
            selected_rows.remove(ndx)
        else:
            selected_rows.append(ndx)

    if changed_id == "explorer-figure.selectedData":
        points = explorerSelectedData["points"]
        ndxs = [virtual_ndxs[p["pointIndex"]] for p in points]
        selected_rows.extend(ndxs)

    selected_rows = list(dict.fromkeys(selected_rows))

    return selected_rows


if __name__ == "__main__":
    app.run_server(debug=True)
