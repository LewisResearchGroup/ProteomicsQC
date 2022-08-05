import os
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


algorithm_options = [
    #{'label': 'Angle-base Outlier Detection', 'value': 'abod'},
    #{'label': 'Clustering-Based Local Outlier', 'value': 'cluster'},
    #{'label': 'Connectivity-Based Outlier Factor', 'value': 'cof'},
    #{'label': 'Histogram-based Outlier Detection', 'value': 'histogram'},
    #{'label': 'k-Nearest Neighbors Detector', 'value': 'knn'},
    #{'label': 'Local Outlier Factor', 'value': 'lof'},
    #{'label': 'One-class SVM detector', 'value': 'svm'},
    #{'label': 'Principal Component Analysis', 'value': 'pca'},
    #{'label': 'Minimum Covariance Determinant', 'value': 'mcd'},
    #{'label': 'Subspace Outlier Detection', 'value': 'sod'},
    #{'label': 'Stochastic Outlier Selection', 'value': 'sos'},
    {'label': 'Isolation Forest', 'value': 'iforest'}
]

layout = html.Div(
    [
        html.H1("Anomaly detection"),
        dcc.Dropdown(id='anomaly-algorithm', options=algorithm_options, value='iforest'),
        html.Button("Predict Anomalies", id="anomaly-btn", className="btn"),
        dcc.Checklist(
            id="anomaly-checklist",
            options=checklist_options,
            value=["hide_rejected"],
            style=dict(padding="15px"),
        ),
        dcc.Loading(
            [dcc.Graph(id="anomaly-figure")],
        ),
    ]
)


def callbacks(app):
    @app.callback(
        Output("shapley-values", "children"),
        Input("anomaly-btn", "n_clicks"),
        State("anomaly-algorithm", 'value'),
        State("project", "value"),
        State("pipeline", "value"),
        State("qc-table-columns", "value"),
    )
    def run_anomaly_detection(n_clicks, algorithm, project, pipeline, columns, **kwargs):
        if n_clicks is None:
            raise PreventUpdate

        uid = kwargs["user"].uuid

        pqc = ProteomicsQC(
            host=os.getenv("OMICS_URL", "http://localhost:8000"),
            project_slug=project,
            pipeline_slug=pipeline,
            uid=uid,
        )

        qc_data = pqc.get_qc_data(data_range=None).set_index("RawFile")

        print(f"Run anomaly detection ({algorithm}).")

        predictions, df_shap = T.detect_anomalies(
            qc_data, algorithm=algorithm, columns=columns, fraction=0.1, n_estimators=1000, max_features=max(10, len(columns))
        )

        print('Predictions:', predictions)
        print('Shapley values:', df_shap)

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
        if tab != "anomaly" or shapley_values is None:
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
                title="Anomaly feature score (shapley values)", height=2000
            ),
        )
        fig.update_layout(font=C.figure_font)

        config = T.gen_figure_config(filename="Anomaly-Detection-Shapley-values")
        return fig, config
