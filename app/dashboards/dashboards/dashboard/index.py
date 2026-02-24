import os
import pandas as pd
import numpy as np
from pathlib import Path as P

import dash
from dash import html, dcc
from dash import dash_table as dt
import dash_bootstrap_components as dbc

import plotly.express as px
import panel as pn

pn.extension("plotly")

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from lrg_omics.plotly_tools import (
    plotly_heatmap,
    plotly_bar,
    plotly_histogram,
    set_template,
)
from lrg_omics.proteomics import ProteomicsQC

from scipy.cluster.hierarchy import dendrogram
from scipy.spatial.distance import squareform

import logging

try:
    from . tools import list_to_dropdown_options
    from . import tools as T
except Exception as e:
    logging.warning(f'Trying to import .tools this error occurred:\n{e}')
    from tools import list_to_dropdown_options
    import tools as T

set_template()


if __name__ == "__main__":
    app = dash.Dash(
        __name__,
        external_stylesheets=["/static/css/dashboard.css"],
    )
    import proteins, quality_control, explorer, anomaly
    import config as C
    import tools as T

    app.config.suppress_callback_exceptions = True
else:
    from django_plotly_dash import DjangoDash
    from . import proteins, quality_control, explorer, anomaly
    from . import config as C
    from . import tools as T

    app = DjangoDash(
        "dashboard",
        add_bootstrap_links=True,
        suppress_callback_exceptions=True,
        external_stylesheets=["/static/css/dashboard.css"],
    )

timeout = 360

protein_table_default_cols = []
BUTTON_STYLE = {
    "padding": "6px 16px",
    "backgroundColor": "#e9f3fe",
    "color": "#2994ff",
    "border": "1px solid #2994ff",
    "borderRadius": "1px",
    "cursor": "pointer",
    "fontWeight": 500,
    "fontSize": "14px",
}

layout = html.Div(
    [
        dcc.Loading(dcc.Store(id="store")),
        dcc.Store(id="qc-scope-data"),
        html.Button("", id="B_update", className="pqc-hidden-trigger"),
        html.Div(
            className="pqc-layout",
            children=[
                html.Div(
                    className="pqc-sidebar",
                    children=[
                        html.Div(
                            className="pqc-panel",
                            children=[
                                html.Div(
                                    className="pqc-scope-grid",
                                    children=[
                                        html.Div(
                                            className="pqc-scope-field",
                                            children=[
                                                html.Label("Project", className="pqc-field-label"),
                                                dcc.Dropdown(
                                                    id="project",
                                                    options=T.get_projects(),
                                                    value="lsarp",
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            className="pqc-scope-field",
                                            children=[
                                                html.Label("Pipeline", className="pqc-field-label"),
                                                dcc.Dropdown(id="pipeline", options=[], value=None),
                                            ],
                                        ),
                                        html.Div(
                                            className="pqc-scope-field",
                                            children=[
                                                html.Label("Data Range", className="pqc-field-label"),
                                                dcc.Dropdown(
                                                    id="data-range",
                                                    options=C.data_range_options,
                                                    value=300,
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="pqc-kpi-grid",
                            children=[
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div("Samples", className="pqc-kpi-label"),
                                        html.Div("0", id="kpi-samples", className="pqc-kpi-value"),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div("Median Protein Groups", className="pqc-kpi-label"),
                                        html.Div(
                                            "--",
                                            id="kpi-median-protein-groups",
                                            className="pqc-kpi-value",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div("Median Peptides", className="pqc-kpi-label"),
                                        html.Div("--", id="kpi-median-peptides", className="pqc-kpi-value"),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div("Median MS/MS Identified [%]", className="pqc-kpi-label"),
                                        html.Div("--", id="kpi-median-msms", className="pqc-kpi-value"),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div(
                                            "Median Missed Cleavages Eq1 [%]",
                                            className="pqc-kpi-label",
                                        ),
                                        html.Div(
                                            "--",
                                            id="kpi-median-missed-cleavages",
                                            className="pqc-kpi-value",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div("Median Oxidations [%]", className="pqc-kpi-label"),
                                        html.Div("--", id="kpi-median-oxidations", className="pqc-kpi-value"),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-kpi-card",
                                    children=[
                                        html.Div(
                                            "Median Delta m/z [ppm]",
                                            className="pqc-kpi-label",
                                        ),
                                        html.Div(
                                            "--",
                                            id="kpi-median-mz-delta",
                                            className="pqc-kpi-value",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="pqc-workspace",
                    children=[
                        html.Div(
                            className="pqc-panel pqc-workspace-panel",
                            children=[
                                dcc.Tabs(
                                    id="tabs",
                                    value="quality_control",
                                    className="pqc-tabs",
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
                                html.Div(
                                    id="tabs-content",
                                    className="pqc-canvas",
                                    children=[
                                        dcc.Graph(id="explorer-figure", style={"display": "none"}),
                                        dcc.Graph(
                                            id="explorer-scatter-matrix",
                                            style={"display": "none"},
                                        ),
                                    ],
                                ),
                                dcc.Loading(
                                    html.Div(
                                        id="qc-table-div",
                                        className="pqc-table-wrap",
                                        style={"display": "none"},
                                        children=[dt.DataTable(id="qc-table")],
                                    )
                                ),
                            ],
                        )
                    ],
                ),
            ],
        ),
        html.Div(id="selection-output"),
        html.Div(id="selected-raw-files", style={"display": "none"}),
        dcc.Loading(html.Div(id="shapley-values", style={"display": "none"})),
        html.Div(
            [
                dcc.Dropdown(
                    id="qc-table-columns",
                    multi=True,
                    options=list_to_dropdown_options(C.qc_columns_options),
                    value=C.qc_columns_default,
                ),
                html.Button("Apply", id="qc-update-table"),
                html.Button("Clear Selection", id="qc-clear-selection"),
                html.Button("Remove Unselected", id="qc-remove-unselected"),
                html.Button("Use Downstream", id="accept"),
                html.Button("Prevent Downstream", id="reject"),
                html.Div(id="accept-reject-output"),
            ],
            style={"display": "none"},
        ),
    ],
    className="pqc-dashboard-root",
)

app.layout = layout

proteins.callbacks(app)
explorer.callbacks(app)
anomaly.callbacks(app)
quality_control.callbacks(app)


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
    return T.get_projects()


@app.callback(
    Output("project", "value"),
    Input("project", "options"),
    State("project", "value"),
)
def pick_default_project(options, current_value):
    if not options:
        return None
    valid_values = [o["value"] for o in options]
    if current_value in valid_values:
        return current_value
    return valid_values[0]


@app.callback(Output("pipeline", "options"), [Input("project", "value")])
def populate_pipelines(project):
    _json = T.get_pipelines(project)
    if len(_json) == 0:
        return []
    else:
        output = [{"label": i["name"], "value": i["slug"]} for i in _json]
        return output


@app.callback(
    Output("pipeline", "value"),
    Input("pipeline", "options"),
    State("pipeline", "value"),
)
def pick_default_pipeline(options, current_value):
    if not options:
        return None
    valid_values = [o["value"] for o in options]
    if current_value in valid_values:
        return current_value
    return valid_values[0]

@app.callback(
    Output("qc-table-div", "children"),
    Output("qc-scope-data", "data"),
    Input("project", "value"),
    Input("pipeline", "value"),
    Input("data-range", "value"),
    State("qc-table-columns", "value"),
)
def refresh_qc_table(project, pipeline, data_range, optional_columns):

    if (project is None) or (pipeline is None):
        return (
            T.table_from_dataframe(pd.DataFrame(), id="qc-table", row_selectable="multi"),
            [],
        )
    optional_columns = optional_columns or C.qc_columns_default
    columns = C.qc_columns_always + optional_columns
    data = T.get_qc_data(
        project=project, pipeline=pipeline, columns=columns, data_range=data_range
    )

    df = pd.DataFrame(data)

    if df.empty:
        return (
            T.table_from_dataframe(df, id="qc-table", row_selectable="multi"),
            [],
        )

    # keep only columns that exist to avoid key errors
    available_cols = [c for c in columns if c in df.columns]

    if "DateAcquired" in df.columns:
        df["DateAcquired"] = pd.to_datetime(df["DateAcquired"], errors="coerce")
    df = df.replace("not detected", np.nan)
    if len(available_cols) > 0:
        df = df[available_cols]

    records = df.to_dict("records")
    return T.table_from_dataframe(df, id="qc-table", row_selectable="multi"), records


@app.callback(
    Output("kpi-samples", "children"),
    Output("kpi-median-protein-groups", "children"),
    Output("kpi-median-peptides", "children"),
    Output("kpi-median-msms", "children"),
    Output("kpi-median-missed-cleavages", "children"),
    Output("kpi-median-oxidations", "children"),
    Output("kpi-median-mz-delta", "children"),
    Input("qc-scope-data", "data"),
)
def update_kpis(data):
    if data is None:
        return "0", "--", "--", "--", "--", "--", "--"
    df = pd.DataFrame(data)
    if df.empty:
        return "0", "--", "--", "--", "--", "--", "--"

    def _median(column, suffix=""):
        if column not in df.columns:
            return "--"
        series = pd.to_numeric(df[column], errors="coerce")
        if series.notna().sum() == 0:
            return "--"
        return f"{series.median():.1f}{suffix}"

    return (
        str(len(df)),
        _median("N_protein_groups"),
        _median("N_peptides"),
        _median("MS/MS Identified [%]", "%"),
        _median("N_missed_cleavages_eq_1 [%]", "%"),
        _median("Oxidations [%]", "%"),
        _median("Uncalibrated - Calibrated m/z [ppm] (ave)"),
    )


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
def update_selected_raw_files_1(selected_rows):
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
        host=os.getenv("OMICS_URL", "http://localhost:8000"),
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
