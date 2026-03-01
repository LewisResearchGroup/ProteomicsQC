import pandas as pd

import plotly.graph_objects as go
import plotly.offline as opy
import plotly.figure_factory as ff

import plotly.io as pio
import plotly.express as px
from dash import dash_table as dt


COLORS = ["rgba(100, 0, 0, 0.5)", "rgba(0, 100, 0, 0.5)", "rgba(0, 0, 100, 0.5)"]


def set_template():
    pio.templates["draft"] = go.layout.Template(
        layout=dict(font={"size": 10}, margin=dict(l=50, r=0, t=100, b=100))
    )

    pio.templates.default = "draft"


def plotly_heatmap(
    df: pd.DataFrame(), x=None, y=None, title=None, max_label_length=None
):
    """
    Creates a heatmap from pandas.DataFrame().
    """

    df = df.copy()

    if isinstance(df.index, pd.MultiIndex):
        df.index = ["_".join([str(i) for i in ndx]) for ndx in df.index]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(i) for i in ndx]) for ndx in df.columns]

    if isinstance(max_label_length, int):
        df.columns = [str(i)[:max_label_length] for i in df.columns]
        df.index = [str(i)[:max_label_length] for i in df.index]

    if x is None:
        x = df.columns
    if y is None:
        y = df.index.to_list()

    fig = go.Figure(data=go.Heatmap(z=df, y=y, x=x, hoverongaps=False))

    fig.update_layout(
        title=title,
    )

    fig.update_layout(
        title={"text": title, "y": 0.9, "x": 0.5, "xanchor": "center", "yanchor": "top"}
    )

    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)

    return fig


def plotly_fig_to_div(fig):
    return opy.plot(fig, auto_open=False, output_type="div")


def plotly_dendrogram(
    df: pd.DataFrame(),
    labels=None,
    orientation="left",
    color_threshold=1,
    height=None,
    width=None,
    max_label_lenght=None,
):

    if labels is None:
        labels = df.index

    if max_label_lenght is not None:
        labels = [i[:max_label_lenght] for i in labels]

    if height is None:
        height = max(500, 10 * len(df))
    fig = ff.create_dendrogram(
        df, color_threshold=color_threshold, labels=labels, orientation=orientation
    )

    fig.update_layout(width=width, height=height, font_family="Monospace")
    fig.update_layout(xaxis_showgrid=True, yaxis_showgrid=True)

    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig


def plotly_bar(df, **kwargs):
    fig = px.bar(df, **kwargs)
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig


def plotly_histogram(df, **kwargs):
    fig = px.histogram(df, **kwargs)
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig


def plotly_table(df):
    return dt.DataTable(
        id="table",
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.iloc[::-1].to_dict("records"),
        sort_action="native",
        sort_mode="single",
        row_selectable="multi",
        row_deletable=True,
        selected_rows=[],
        filter_action="native",
        page_action="native",
        page_current=0,
        page_size=16,
        style_table={"overflowX": "scroll"},
        export_format="csv",
        export_headers="display",
        merge_duplicate_headers=True,
        style_cell={"font_size": "10px", "padding-left": "1em", "padding-right": "1em"},
    )


def lines_plot(rawtools_matrix, cols, colors=None, title=None, **kwargs):
    if colors is None:
        colors = COLORS
    fig = go.Figure()
    for i, col in enumerate(cols):
        fig.add_trace(
            go.Scatter(
                x=rawtools_matrix.index,
                y=rawtools_matrix[col],
                name=col,
                mode="lines",
                line=dict(width=0.5, color=colors[i]),
                **kwargs
            ),
        )
    fig.update_layout(
        legend_title_text="",
        autosize=True,
        title=title,
        legend=dict(orientation="h"),
        margin=dict(l=50, r=10, b=50, t=50, pad=0),
    )
    fig.update_xaxes(title_text=rawtools_matrix.index.name)
    return fig


def histograms(rawtools_matrix, cols=None, title=None, colors=None):
    if cols is None:
        cols = ["ParentIonMass"]
    if colors is None:
        colors = COLORS
    fig = go.Figure()
    if len(cols) == 1:
        fig.update_layout(title=cols[0])
        fig.update_layout(showlegend=False)
    for i, col in enumerate(cols):
        fig.add_trace(
            go.Histogram(
                x=rawtools_matrix[col],
                visible="legendonly" if i > 0 else None,
                name=col,
                marker_color=colors[i],
            )
        )
    fig.update_layout(legend_title_text="")
    fig.update_layout(barmode="overlay")
    fig.update_traces(opacity=0.75)
    fig.update_layout(title=title)
    fig.update_layout(
        legend_title_text="",
        autosize=True,
        title=title,
        legend=dict(orientation="h"),
        margin=dict(l=50, r=10, b=50, t=50, pad=0),
    )
    return fig
