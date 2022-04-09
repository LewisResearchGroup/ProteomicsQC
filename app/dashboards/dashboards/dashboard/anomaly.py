import logging
import pandas as pd
import numpy as np

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import dash_table as dt

from plotly import express as px

from dash_tabulator import DashTabulator

from lrg_omics.proteomics import ProteomicsQC

try:
    from . import tools as T
    from . import config as C
except Exception as e:
    logging.warning(e)
    import tools as T
    import config as C


checklist_options = [
    {"label": "Hide rejected samples", "value": "hide_rejected"},
]

layout = html.Div(
    [
        html.H1("Anomaly detection"),
        html.Button("Run isolation forest", id="anomaly-btn", className="btn"),
        dcc.Checklist(
            id="anomaly-checklist",
            options=checklist_options,
            value=["hide_rejected"],
            style=dict(padding="15px"),
        ),
        dcc.Loading(
            [dcc.Graph(id="anomaly-figure")],
        ),
        dcc.Markdown("Anormal feature values have lower z-values."),
    ]
)


def callbacks(app):
    @app.callback(
        Output("shapley-values", "children"),
        Input("anomaly-btn", "n_clicks"),
        State("project", "value"),
        State("pipeline", "value"),
    )
    def run_anomaly_detection(n_clicks, project, pipeline, **kwargs):
        if n_clicks is None:
            raise PreventUpdate

        uid = kwargs["user"].uuid

        pqc = ProteomicsQC(
            host=os.getenv('OMICS_URL', None),
            project_slug=project,
            pipeline_slug=pipeline,
            uid=uid,
        )

        qc_data = pqc.get_qc_data(data_range=None).set_index("RawFile")

        predictions, df_shap = T.detect_anomalies(
            qc_data, fraction=0.05, n_estimators=1000
        )

        # Update flags
        currently_unflagged = list(qc_data[~qc_data.Flagged].reset_index().RawFile)
        currently_flagged = list(qc_data[qc_data.Flagged].reset_index().RawFile)
        files_to_flag = predictions[predictions.Anomaly == 1].index.to_list()
        files_to_unflag = predictions[predictions.Anomaly == 0].index.to_list()
        files_to_flag = [i for i in files_to_flag if i in currently_unflagged]
        files_to_unflag = [i for i in files_to_unflag if i in currently_flagged]
        pqc.rawfile(files_to_flag, "flag")
        pqc.rawfile(files_to_unflag, "unflag")

        return df_shap.to_json()

    @app.callback(
        Output("anomaly-figure", "figure"),
        Output("anomaly-figure", "config"),
        Input("shapley-values", "children"),
        Input("qc-table", "data"),
        Input("anomaly-checklist", "value"),
        Input("qc-table", "derived_virtual_indices"),
        Input("tabs", "value"),
    )
    def plot_shapley(shapley_values, qc_data, options, ndxs, tab):
        if tab != "anomaly":
            raise PreventUpdate

        df_shap = pd.read_json(shapley_values)

        qc_data = pd.DataFrame(qc_data)
        qc_data = qc_data.iloc[ndxs]

        if "hide_rejected" in options:
            qc_data = qc_data[qc_data["Use Downstream"] != False]

        fns = qc_data["RawFile"]
        df_shap = df_shap.loc[fns]

        fig = T.px_heatmap(
            df_shap.T,
            layout_kws=dict(
                title="Anomaly feature score (shapley values)", height=1200
            ),
        )
        fig.update_layout(font=C.figure_font)

        config = T.gen_figure_config(filename="Anomaly-Detection-Shapley-values")
        return fig, config
