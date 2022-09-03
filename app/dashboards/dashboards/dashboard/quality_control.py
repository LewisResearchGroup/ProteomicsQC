import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from . import tools as T
    from . import config as C

except:
    import tools as T
    import config as C


x_options = [
    dict(label=x, value=x)
    for x in [
        "Index",
        "RawFile",
        "DateAcquired",
    ]
]

layout = html.Div(
    [
        html.Div(
            [html.P(["x-Axis:", dcc.Dropdown(id="x", options=x_options, value='Index')])],
            style={"width": "100%", "margin": "auto"},
        ),
        html.Div(
            [html.Button("Refresh Plots", id="refresh-plots", className="btn")],
            style={"margin-bottom": 100},
        ),
        dcc.Loading(
            [
                html.Div(
                    [
                        dcc.Graph(id="qc-figure", style={"max-width": "100%"}),
                    ],
                    style={"textAlign": "center"},
                )
            ]
        ),
        # placeholders for callbacks
        dcc.Graph(id="explorer-figure", style={"visibility": "hidden"}),
        dcc.Graph(id="explorer-scatter-matrix", style={"visibility": "hidden"}),
    ]
)


def callbacks(app):
    @app.callback(
        Output("qc-figure", "figure"),
        Output("qc-figure", "config"),
        Input("refresh-plots", "n_clicks"),
        State("qc-table", "selected_rows"),
        State("qc-table", "derived_virtual_indices"),
        State("x", "value"),
        State("qc-table", "data"),
        State("qc-table-columns", "value"),
    )
    def plot_qc_figure(refresh, selected, ndxs, x, data, optional_columns):
        """Creates the bar-plot figure"""
        if (data is None) or (ndxs is None) or (len(ndxs) == 0):
            raise PreventUpdate

        if x is None:
            x = "RawFile"

        df = pd.DataFrame(data)

        df['Selected'] = False
        df.loc[selected, 'Selected'] = True

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
                hovertext=df.RawFile + '<br>' + df.DateAcquired.astype(str),
                text=None if x == "RawFile" else df["RawFile"],
            )
            fig.add_trace(trace, row=1 + i, col=1)

        fig.update_layout(
            hovermode="closest",
            hoverlabel_namelength=-1,
            height=500 + 250 * (i + 1),
            showlegend=False,
            margin=dict(l=None, r=None, b=500, t=None, pad=0),
            font=C.figure_font,
            yaxis={"automargin": True},
        )

        marker_color = df[["Use Downstream", "Flagged", "Selected"]].apply(lambda row: T.get_marker_color(*row), axis=1)
        marker_line_color = df[["Use Downstream", "Flagged", "Selected"]].fillna('unknown').apply(lambda row: T.get_marker_line_color(*row), axis=1)

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
                    tickmode="array",
                    tickvals=tuple(range(len(df))),
                    ticktext=tuple(df[x]),
                )
            )

        config = T.gen_figure_config(filename="QC-barplot")

        return fig, config
