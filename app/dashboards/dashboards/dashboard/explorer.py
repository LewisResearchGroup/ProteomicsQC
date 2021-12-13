import pandas as pd
import plotly.express as px
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

try:
    from . import config as C
    from . import tools as T
except:
    import config as C 
    import tools as T

all_columns = C.qc_columns_default + C.qc_columns_options + C.qc_columns_always
res = []
[res.append(x) for x in all_columns if x not in res]
all_columns = res

layout = html.Div(
    [
        dcc.Markdown("---"),
        html.H2("Explorer"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Button("Refresh Plots", id="refresh-explorer-plot", className="btn", style={"margin-bottom": 5}),
                                dcc.Dropdown(
                                    id="explorer-x",
                                    multi=False,
                                    options=T.list_to_dropdown_options(all_columns),
                                    placeholder="X-axis",
                                    value=all_columns[0],
                                ),
                                dcc.Dropdown(
                                    id="explorer-y",
                                    multi=False,
                                    options=T.list_to_dropdown_options(all_columns),
                                    placeholder="Y-axis",
                                    value=all_columns[1],
                                ),
                                dcc.Dropdown(
                                    id="explorer-color",
                                    multi=False,
                                    options=T.list_to_dropdown_options(all_columns),
                                    placeholder="Color",
                                    value=all_columns[2],
                                ),
                                dcc.Dropdown(
                                    id="explorer-size",
                                    multi=False,
                                    options=T.list_to_dropdown_options(all_columns),
                                    placeholder="Marker size",
                                    value=all_columns[3],
                                ),
                                dcc.Dropdown(
                                    id="explorer-facet-row",
                                    multi=False,
                                    options=T.list_to_dropdown_options(all_columns),
                                    placeholder="Facet row",
                                    value=None,
                                ),
                                dcc.Dropdown(
                                    id="explorer-facet-col",
                                    multi=False,
                                    options=T.list_to_dropdown_options(all_columns),
                                    placeholder="Facet column",
                                    value=None,
                                ),
                            ],
                            style={"padding-top": 100, "margin": "auto"},
                            className="center",
                        ),
                    ],
                    style={"width": 300, "min-width": 300, "max-width": 300},
                ),
                dbc.Col(
                    [
                        dcc.Loading(
                            [
                                html.Div(style={"min-width": 300}),
                                dcc.Graph(
                                    id="explorer-figure", style={"max-width": "100%"}
                                ),
                                 dcc.Graph(
                                    id="qc-figure", style={"max-width": "100%", "visibility":"hidden"}
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        ),
    ]
)


def callbacks(app):
    
    # EXPLORER Callbacks
    @app.callback(
        [Output("explorer-figure", "figure"), Output("explorer-figure", "config")],
        [
            Input("refresh-explorer-plot", "n_clicks"),

        ],
        [
            State("explorer-x", "value"),
            State("explorer-y", "value"),
            State("explorer-color", "value"),
            State("explorer-size", "value"),
            State("explorer-facet-row", "value"),
            State("explorer-facet-col", "value"),
            State("qc-table", "data"),
            State("qc-table", "selected_rows"),
            State("qc-table", "derived_virtual_indices")            
        ],
    )
    def explorer_plot(n_clicks,
        x, y, color, size, facet_row, facet_col, data, selected, ndxs
    ):
    
        #print('derived_virtual_indices:', ndxs)
        #print('selected_rows:', selected)

        columns = [
            x,
            y,
            color,
            size,
            facet_row,
            facet_col,
        ]

        if y is None:
            raise PreventUpdate

        if None in columns:
            columns.remove(None)

        columns = [c for c in columns if (c is not None)]

        df = pd.DataFrame(data)
        df["DateAcquired"] = pd.to_datetime(df["DateAcquired"])

        #print(df)
        if ndxs is not None: df = df.reindex(ndxs)
        #print(df)

        if facet_row is not None:
            n_rows = len(df[facet_row].value_counts())
        else:
            n_rows = 2

        facet_col_wrap = 3
        if facet_col is not None:
            n_cols = len(df[facet_col].value_counts())
            n_rows = min(2, int(n_cols / facet_col_wrap) + 2)

        if size is not None:
            # Plotly crashes if size column has NaNs
            df[size] = df[size].fillna(0)

        fig = px.scatter(
            data_frame=df,
            x=x,
            y=y,
            color=color,
            size=size,
            facet_row=facet_row,
            facet_col=facet_col,
            hover_data=["Index", "RawFile"],
            facet_col_wrap=facet_col_wrap,
        )

        fig.update_layout(
            autosize=True,
            height=300 * n_rows + 200,
            showlegend=False,
            margin=dict(l=50, r=10, b=200, t=50, pad=0),
            hovermode="closest",
        )

        config = T.gen_figure_config(filename="QC-scatter")

        
        marker_color = df["Use Downstream"].replace(
            {True: C.colors['use_downstream'], False: C.colors['dont_use_downstream']}
        )
        marker_line_color = df["Flagged"].replace(
            {True: C.colors['flagged'], False: C.colors['not_flagged']}
        )
        marker_symbol = [0] * len(df)

        for i, ndx in enumerate(ndxs):
            if ndx in selected:
                marker_color[i] = C.colors['selected']
                marker_symbol[i] = 1

        marker_size = [100] * len(df)

        fig.update_traces(
            marker_symbol=marker_symbol,
            marker_line_color=marker_line_color,
            marker_line_width=3,
            opacity=1,
        )

        if color is None:
            fig.update_traces(marker_color=marker_color)

        if size is None:
            fig.update_traces(marker_size=20)

        return fig, config

    @app.callback(
        Output('explorer-x', 'options'),
        Output('explorer-y', 'options'),
        Output('explorer-color', 'options'),
        Output('explorer-size', 'options'),
        Output('explorer-facet-row', 'options'),
        Output('explorer-facet-col', 'options'),        
        Input('qc-table', 'data')
    )
    def update_dropdowns(data):
        print('Updating dropdowns')
        cols = pd.DataFrame(data).columns
        options = T.list_to_dropdown_options(cols)
        return [options]*6
