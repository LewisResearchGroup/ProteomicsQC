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

from pycaret.anomaly import setup, create_model, save_model, load_model

from lrg_omics.proteomics import ProteomicsQC

try:
    from .tools import list_to_dropdown_options
    from . import tools as T
except:
    from tools import list_to_dropdown_options
    import tools as T


layout = html.Div(
    [
        html.H1("Anomaly detection"),
        html.Button("Run isolation forest", id="anomaly-btn"),
        dcc.Loading(
            [dcc.Graph(id="anomaly-figure")],
        )
    ]
)


def callbacks(app):
    @app.callback(
        Output("anomaly-figure", "figure"),
        Input("anomaly-btn", "n_clicks"),
        State("qc-table", "data"),
        State("project", "value"),
        State("pipeline", "value"),
    )
    def run_anomaly_detection(n_clicks, data, project, pipeline):

        print('Anomaly detection', project, pipeline)

        pqc = ProteomicsQC(
            host='http://localhost:8000',
            project_slug=project, 
            pipeline_slug=pipeline,
        )

        qc_data = pqc.get_qc_data(data_range=None).set_index('RawFile')

        log_cols = ['Ms1MedianSummedIntensity', 'Ms2MedianSummedIntensity', 'MedianPrecursorIntensity']

        for c in log_cols: qc_data[c] = qc_data[c].apply(T.log2p1)

        df_train = qc_data[qc_data['Use Downstream']].select_dtypes(include=np.number).drop('Index', axis=1).fillna(0)
        df_test = qc_data[~qc_data['Use Downstream']].fillna(0)[df_train.columns]
        df_all = qc_data.fillna(0)[df_train.columns]

        _ = setup(df_train, silent=True, ignore_low_variance=True, remove_perfect_collinearity=True)

        model_name = 'iforest'
        model = create_model(model_name)

        save_model(model, 'model')
        saved_model = load_model('model')
        _data = saved_model[:-1].transform(df_all)
        _model = saved_model.named_steps["trained_model"]

        sa = T.ShapAnalysis(_model, _data)

        fig = T.px_heatmap(sa.df_shap, 
                           layout_kws=dict(title='Anomaly feature importance', 
                                           height=1000))

        return fig