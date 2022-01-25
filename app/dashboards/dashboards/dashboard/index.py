import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path as P

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
from lrg_omics.proteomics import ProteomicsQC

from plotly.subplots import make_subplots
import plotly.graph_objects as go

from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import pdist, squareform

import logging

try:
    from .tools import list_to_dropdown_options
    from . import tools as T
except Exception as e:
    logging.warngin(e)
    from tools import list_to_dropdown_options
    import tools as T

set_template()


if __name__ == "__main__":
    app = dash.Dash(__name__)
    import proteins, quality_control, explorer, anomaly
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
    from . import proteins, quality_control, explorer, anomaly

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
                                        id="tab-anomaly",
                                        label="Anomaly detection",
                                        value="anomaly",
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
                            html.Button(
                                "Clear Selection",
                                id="qc-clear-selection",
                                className="btn",
                            ),
                            html.Button(
                                "Remove unselected",
                                id="qc-remove-unselected",
                                className="btn",
                            ),
                            html.Button(
                                "Use downstream",
                                id="accept",
                                className="btn",
                            ),
                            html.Button(
                                "Prevent downstream",
                                id="reject",
                                className="btn",
                            ),
                            html.Div(
                                id="accept-reject-output",
                                style={
                                    "visibility": "visible",
                                    "width": "300px",
                                    "float": "right",
                                },
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
        html.Div(id="selected-raw-files", style={"visibility": "hidden"}),
        dcc.Loading(html.Div(id="shapley-values", style={"visibility": "hidden"})),
    ],
    style={"max-width": "90%", "display": "block", "margin": "auto"},
)

app.layout = layout

proteins.callbacks(app)
explorer.callbacks(app)
anomaly.callbacks(app)


@app.callback(Output("tabs-content", "children"), [Input("tabs", "value")])
def render_content(tab):
    if tab == "proteins":
        return proteins.layout
    if tab == "quality_control":
        return quality_control.layout
    if tab == "explorer":
        return explorer.layout
    if tab == "anomaly":
        return anomaly.layout


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
    Input("qc-update-table", "n_clicks"),
    Input("pipeline", "value"),
    State("project", "value"),
    State("qc-table-columns", "value"),
    State("data-range", "value"),
)
def refresh_qc_table(n_clicks, pipeline, project, optional_columns, data_range):

    if (project is None) or (pipeline is None):
        raise PreventUpdate
    columns = C.qc_columns_always + optional_columns
    data = get_qc_data(
        project=project, pipeline=pipeline, columns=columns, data_range=data_range
    )

    df = pd.DataFrame(data)

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

    fig.update_layout(
        hovermode="closest",
        hoverlabel_namelength=-1,
        height=200 + 250 * (i + 1),
        showlegend=False,
        margin=dict(l=50, r=10, b=200, t=50, pad=0),
    )

    marker_color = df["Use Downstream"].replace(
        {True: C.colors["accepted"], False: C.colors["rejected"], None: C.colors["unassigned"]}
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
    Input("qc-clear-selection", "n_clicks"),
    Input("qc-remove-unselected", "n_clicks"),
    Input("qc-figure", "selectedData"),
    Input("qc-figure", "clickData"),
    Input("explorer-figure", "selectedData"),
    Input("explorer-figure", "clickData"),
    Input("explorer-scatter-matrix", "selectedData"),
    Input("explorer-scatter-matrix", "clickData"),
    Input("qc-update-table", "n_clicks"),
    State("qc-table", "selected_rows"),
    State("qc-table", "derived_virtual_indices"),
)
def update_table_selection(
    clear,
    remove_unselected,
    selectedData,
    clickData,
    explorerSelectedData,
    explorerClickData,
    explorerScatterMatrixSelectedData,
    explorerScatterMatrixClickData,
    table_refresh,
    selected_rows,
    virtual_ndxs,
):

    # Workaround a bug, this callback is triggered without trigger
    if len(dash.callback_context.triggered) == 0:
        raise PreventUpdate

    changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]

    if changed_id == "qc-clear-selection.n_clicks":
        return []
    if changed_id == "qc-remove-unselected.n_clicks":
        return []

    if (
        (selectedData is None)
        and (clickData is None)
        and (explorerSelectedData is None)
        and (explorerClickData is None)
        and (explorerScatterMatrixSelectedData is None)
        and (explorerScatterMatrixClickData is None)
    ):
        raise PreventUpdate

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

    if changed_id == "explorer-scatter-matrix.clickData":
        ndx = explorerScatterMatrixClickData["points"][0]["pointIndex"]
        ndx = virtual_ndxs[ndx]
        if ndx in selected_rows:
            selected_rows.remove(ndx)
        else:
            selected_rows.append(ndx)

    if changed_id == "explorer-scatter-matrix.selectedData":
        points = explorerScatterMatrixSelectedData["points"]
        ndxs = [virtual_ndxs[p["pointIndex"]] for p in points]
        selected_rows.extend(ndxs)

    selected_rows = list(dict.fromkeys(selected_rows))

    return selected_rows


@app.callback(
    Output("qc-table", "data"),
    Input("qc-remove-unselected", "n_clicks"),
    State("qc-table", "data"),
    State("qc-table", "selected_rows"),
)
def restrict_to_selection(n_clicks, data, selected):
    if n_clicks is None:
        raise PreventUpdate

    # Workaround a bug, this callback is triggered without trigger
    if len(dash.callback_context.triggered) == 0:
        raise PreventUpdate

    df = pd.DataFrame(data)
    df["DateAcquired"] = pd.to_datetime(df["DateAcquired"])
    df = df.reindex(selected)
    return df.to_dict("records")


@app.callback(
    Output("selected-raw-files", "children"),
    Input("qc-table", "selected_rows"),
)
def update_selected_raw_files(selected_rows):
    return selected_rows


@app.callback(
    Output("accept-reject-output", "children"),
    Input("accept", "n_clicks"),
    Input("reject", "n_clicks"),
    State("selected-raw-files", "children"),
    State("qc-table", "data"),
    State("project", "value"),
    State("pipeline", "value"),
)
def update_selected_raw_files(
    accept, reject, selection, data, project, pipeline, **kwargs
):
    if ((accept is None) and (reject is None)) or (not selection):
        raise PreventUpdate

    uid = kwargs["user"].uuid

    changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]
    if changed_id == "accept.n_clicks":
        action = "accept"
    if changed_id == "reject.n_clicks":
        action = "reject"

    data = pd.DataFrame(data)

    data = data.iloc[selection]

    raw_files = data.RawFile.values

    raw_files = [P(i).with_suffix(".raw") for i in raw_files]

    pqc = ProteomicsQC(
        host="http://localhost:8000",
        project_slug=project,
        pipeline_slug=pipeline,
        uid=uid,
    )

    response = pqc.rawfile(raw_files, action)

    if response["status"] == "success":
        return dbc.Alert("Success", color="success")
    return dbc.Alert(response["status"], color="danger")


if __name__ == "__main__":
    app.run_server(debug=True)
