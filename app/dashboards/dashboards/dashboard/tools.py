import os
from select import select
import sys
import json
import logging
from xml.etree.ElementPath import _SelectorContext
import requests
import shap
import pandas as pd
import dash_table as dt
from dash_table import DataTable
from dash_table.Format import Format
import plotly.express as px
import plotly.graph_objects as go
from matplotlib import pyplot as pl
from numpy import NaN

from pandas.api.types import is_numeric_dtype


from pycaret.anomaly import (
    setup,
    create_model,
    save_model,
    load_model,
    get_config,
    predict_model,
)

URL = os.getenv("OMICS_URL", "http://localhost:8000")

logging.info(f"Dashboard API URL:{URL}", file=sys.stderr)


def list_to_dropdown_options(values):
    return [{"label": v, "value": v} for v in values]


def table_from_dataframe(df, id="table", row_deletable=True, row_selectable="multi"):
    return dt.DataTable(
        id=id,
        columns=[
            {"name": i, "id": i, "format": Format(precision=2)} for i in df.columns
        ],
        data=df.iloc[::-1].to_dict("records"),
        sort_action="native",
        sort_mode="single",
        row_selectable=row_selectable,
        row_deletable=row_deletable,
        selected_rows=[],
        filter_action="native",
        page_action="native",
        page_current=0,
        page_size=16,
        style_table={"overflowX": "scroll"},
        export_format="csv",
        export_headers="display",
        merge_duplicate_headers=True,
        style_cell={"font_size": "10px", "padding-left": "5em", "padding-right": "5em"},
    )


def get_projects():
    url = f"{URL}/api/projects"
    try:
        _json = requests.post(url).json()
    except:
        return []
    output = [{"label": i["name"], "value": i["slug"]} for i in _json]
    return output


def get_pipelines(project):
    url = f"{URL}/api/pipelines"
    headers = {"Content-type": "application/json"}
    data = json.dumps(dict(project=project))
    return requests.post(url, data=data, headers=headers).json()


def get_protein_groups(
    project, pipeline, protein_names=None, columns=None, data_range=None, raw_files=None
):
    url = f"{URL}/api/protein-groups"
    headers = {"Content-type": "application/json"}
    data = json.dumps(
        dict(
            project=project,
            pipeline=pipeline,
            protein_names=protein_names,
            columns=columns,
            data_range=data_range,
            raw_files=raw_files,
        )
    )
    res = requests.post(url, data=data, headers=headers).json()
    return res


def get_protein_names(
    project,
    pipeline,
    remove_contaminants=True,
    remove_reversed_sequences=True,
    data_range=None,
    raw_files=None,
):
    url = f"{URL}/api/protein-names"
    headers = {"Content-type": "application/json"}
    data = json.dumps(
        dict(
            project=project,
            pipeline=pipeline,
            remove_contaminants=remove_contaminants,
            remove_reversed_sequences=remove_reversed_sequences,
            data_range=data_range,
            raw_files=raw_files,
        )
    )
    _json = requests.post(url, data=data, headers=headers).json()
    return _json


def get_qc_data(project, pipeline, columns, data_range=None):
    url = f"{URL}/api/qc-data"
    headers = {"Content-type": "application/json"}
    data = json.dumps(
        dict(project=project, pipeline=pipeline, columns=columns, data_range=data_range)
    )
    return requests.post(url, data=data, headers=headers).json()


def gen_figure_config(
    filename="plot", format="svg", height=None, width=None, scale=None, editable=True
):
    config = {
        "toImageButtonOptions": {"format": format, "filename": filename},
        "height": height,
        "width": width,
        "scale": scale,
        "editable": editable,
    }
    return config


def gen_tabulator_columns(
    col_names=None,
    add_ms_file_col=False,
    add_color_col=False,
    add_peakopt_col=False,
    add_ms_file_active_col=False,
    col_width="12px",
    editor="input",
):

    if col_names is None:
        col_names = []
    else:
        col_names = list(col_names)

    columns = [
        {
            "formatter": "rowSelection",
            "titleFormatter": "rowSelection",
            "titleFormatterParams": {"rowRange": "active"},
            "hozAlign": "center",
            "headerSort": False,
            "width": "1px",
            "frozen": True,
        }
    ]

    for col in col_names:
        content = {
            "title": col,
            "field": col,
            "headerFilter": True,
            "width": col_width,
            "editor": editor,
        }

        columns.append(content)

    return columns


def log2p1(x):
    try:
        return np.log2(x + 1)
    except:
        return x


class ShapAnalysis:
    def __init__(self, model, df):
        #explainer = shap.TreeExplainer(model)
        explainer = shap.Explainer(model)
        
        shap_values = explainer(df)
        self._shap_values = shap_values
        self._instance_names = df.index.to_list()
        self._feature_names = df.columns.to_list()
        self.df_shap = pd.DataFrame(
            shap_values.values, columns=df.columns, index=df.index
        )

    def waterfall(self, i, **kwargs):
        shap_values = self._shap_values
        self._base_values = shap_values[i][0].base_values
        self._values = shap_values[i].values
        shap_object = shap.Explanation(
            base_values=self._base_values,
            values=self._values,
            feature_names=self._feature_names,
            # instance_names = self._instance_names,
            data=shap_values[i].data,
        )
        shap.plots.waterfall(shap_object, **kwargs)

    def summary(self, **kwargs):
        shap.summary_plot(self._shap_values, **kwargs)

    def bar(self, **kwargs):
        shap.plots.bar(self._shap_values, **kwargs)
        for ax in pl.gcf().axes:
            for ch in ax.get_children():
                try:
                    ch.set_color("0.3")
                except:
                    break


def px_heatmap(df, colorscale="jet_r", layout_kws=None):
    fig = go.Figure(
        data=go.Heatmap(z=df.values, y=df.index, x=df.columns, colorscale=colorscale)
    )
    fig.update_layout(**layout_kws)
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig


def plotly_heatmap(
    df,
    normed_by_cols=False,
    transposed=False,
    clustered=False,
    add_dendrogram=False,
    name="",
    x_tick_colors=None,
    height=None,
    width=None,
    correlation=False,
    call_show=False,
    verbose=False,
):

    max_is_not_zero = df.max(axis=1) != 0
    non_zero_labels = max_is_not_zero[max_is_not_zero].index
    df = df.loc[non_zero_labels]

    plot_type = "Heatmap"
    colorscale = "Bluered"
    plot_attributes = []

    if normed_by_cols:
        df = df.divide(df.max()).fillna(0)
        plot_attributes.append("normalized")

    if transposed:
        df = df.T

    if correlation:
        plot_type = "Correlation"
        df = df.corr()
        colorscale = [
            [0.0, "rgb(165,0,38)"],
            [0.1111111111111111, "rgb(215,48,39)"],
            [0.2222222222222222, "rgb(244,109,67)"],
            [0.3333333333333333, "rgb(253,174,97)"],
            [0.4444444444444444, "rgb(254,224,144)"],
            [0.5555555555555556, "rgb(224,243,248)"],
            [0.6666666666666666, "rgb(171,217,233)"],
            [0.7777777777777778, "rgb(116,173,209)"],
            [0.8888888888888888, "rgb(69,117,180)"],
            [1.0, "rgb(49,54,149)"],
        ]
    else:
        plot_type = "Heatmap"

    if clustered:
        dendro_side = ff.create_dendrogram(
            df,
            orientation="right",
            labels=df.index.to_list(),
            color_threshold=0,
            colorscale=["black"] * 8,
        )
        dendro_leaves = dendro_side["layout"]["yaxis"]["ticktext"]
        df = df.loc[dendro_leaves, :]
        if correlation:
            df = df[df.index]

    x = df.columns
    if clustered:
        y = dendro_leaves
    else:
        y = df.index.to_list()
    z = df.values

    heatmap = go.Heatmap(x=x, y=y, z=z, colorscale=colorscale)

    if name == "":
        title = ""
    else:
        title = f'{plot_type} of {",".join(plot_attributes)} {name}'

    # Figure without side-dendrogram
    if (not add_dendrogram) or (not clustered):
        fig = go.Figure(heatmap)
        fig.update_layout(
            {"title_x": 0.5},
            title={"text": title},
            yaxis={"title": "", "tickmode": "array", "automargin": True},
        )

        fig.update_layout({"height": height, "width": width, "hovermode": "closest"})

    else:  # Figure with side-dendrogram
        fig = go.Figure()

        for i in range(len(dendro_side["data"])):
            dendro_side["data"][i]["xaxis"] = "x2"

        for data in dendro_side["data"]:
            fig.add_trace(data)

        y_labels = heatmap["y"]
        heatmap["y"] = dendro_side["layout"]["yaxis"]["tickvals"]

        fig.add_trace(heatmap)

        fig.update_layout(
            {
                "height": height,
                "width": width,
                "showlegend": False,
                "hovermode": "closest",
                "paper_bgcolor": "white",
                "plot_bgcolor": "white",
                "title_x": 0.5,
            },
            title={"text": title},
            # X-axis of main figure
            xaxis={
                "domain": [0.11, 1],
                "mirror": False,
                "showgrid": False,
                "showline": False,
                "zeroline": False,
                "showticklabels": True,
                "ticks": "",
            },
            # X-axis of side-dendrogram
            xaxis2={
                "domain": [0, 0.1],
                "mirror": False,
                "showgrid": True,
                "showline": False,
                "zeroline": False,
                "showticklabels": False,
                "ticks": "",
            },
            # Y-axis of main figure
            yaxis={
                "domain": [0, 1],
                "mirror": False,
                "showgrid": False,
                "showline": False,
                "zeroline": False,
                "showticklabels": False,
            },
        )

        fig["layout"]["yaxis"]["ticktext"] = np.asarray(y_labels)
        fig["layout"]["yaxis"]["tickvals"] = np.asarray(
            dendro_side["layout"]["yaxis"]["tickvals"]
        )

    fig.update_layout(
        # margin=dict( l=50, r=10, b=200, t=50, pad=0 ),
        autosize=True,
        hovermode="closest",
    )

    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)

    if call_show:
        fig.show(config={"displaylogo": False})
    else:
        return fig


def detect_anomalies(qc_data, algorithm=None, columns=None, max_features=None, precentage=None, **model_kws):
    
    selected_cols = [c for c in columns if is_numeric_dtype(qc_data[c])]
    selected_cols.reverse()
    if max_features is not None:
        max_features = max(max_features, len(selected_cols))
    for col in selected_cols:
        if not col in qc_data.columns:
            selected_cols.remove(col)
            logging.warning(f'Column not found in QC data: {col}')
    log_cols = [
        "Ms1MedianSummedIntensity",
        "Ms2MedianSummedIntensity",
        "MedianPrecursorIntensity",
    ]
    for c in log_cols:
        qc_data[c] = qc_data[c].apply(log2p1)
    
    df_train = qc_data[qc_data["Use Downstream"] == True][selected_cols].fillna(0)
    df_test = qc_data[qc_data["Use Downstream"] != True][selected_cols].fillna(0)
    df_all = qc_data[selected_cols].fillna(0)

    _ = setup(
        df_train,
        #silent=True,
        #ignore_low_variance=False,
        #remove_perfect_collinearity=False,
        numeric_features=selected_cols,
    )

    logging.info(f'Create anomaly model: {algorithm}')
    model = create_model(algorithm, **model_kws)
    pipeline = get_config("pipeline")
    data = pipeline.transform(df_all)
    # pycaret changes column names
    # change it to original names
    data.columns = selected_cols
    if algorithm == 'iforest':
        sa = ShapAnalysis(model, data)
        shapley_values = sa.df_shap.reindex(selected_cols, axis=1)
    else:
        shapley_values = None
    prediction = predict_model(model, df_all)[["Anomaly", "Anomaly_Score"]]
    return prediction, shapley_values


def get_marker_color(use_downstream, flagged, selected):
    colors = {
        ('unknown', False, False): 'grey',
        ('unknown', True,  False): 'grey',
        ('unknown', False, True):  'black',
        ('unknown', True,  True):  'black',

        (True,  False, False): 'blue',
        (False, False, False): 'deepskyblue',
        (True,  True,  False): 'red',
        (False, True,  False): 'pink',
        (True,  False, True):  'magenta',
        (False, False, True):  'magenta',
        (True,  True,  True):  'cyan',
        (False, True,  True):  'cyan',        
    }
    key = (use_downstream if isinstance(use_downstream, bool) else 'unknown', flagged, selected)
    color = colors[key]
    return color
    

def get_marker_line_color(use_downstream, flagged, selected):
    colors = {
        ('unknown', False, False): 'lightblue',
        ('unknown', True,  False): 'red',
        ('unknown', False, True):  'black',
        ('unknown', True,  True):  'black',

        (True,  False, False): 'deepskyblue',
        (False, False, False): 'lightblue',
        (True,  True,  False): 'red',
        (False, True,  False): 'pink',
        (True,  False, True):  'magenta',
        (False, False, True):  'magenta',
        (True,  True,  True):  'cyan',
        (False, True,  True):  'cyan',        
    }
    color = colors[(use_downstream if isinstance(use_downstream, bool) else 'unknown', flagged, selected)]
    return color