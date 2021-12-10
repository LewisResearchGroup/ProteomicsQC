import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt

try:
    from .tools import list_to_dropdown_options
    from .config import qc_columns_options, qc_columns_default, qc_columns_always
except:
    from tools import list_to_dropdown_options
    from config import qc_columns_options, qc_columns_default, qc_columns_always

all_columns = qc_columns_default + qc_columns_options + qc_columns_always
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
                                dcc.Dropdown(
                                    id="explorer-x",
                                    multi=False,
                                    options=list_to_dropdown_options(all_columns),
                                    placeholder="X-axis",
                                    value=all_columns[0],
                                ),
                                dcc.Dropdown(
                                    id="explorer-y",
                                    multi=False,
                                    options=list_to_dropdown_options(all_columns),
                                    placeholder="Y-axis",
                                    value=all_columns[1],
                                ),
                                dcc.Dropdown(
                                    id="explorer-color",
                                    multi=False,
                                    options=list_to_dropdown_options(all_columns),
                                    placeholder="Color",
                                    value=all_columns[2],
                                ),
                                dcc.Dropdown(
                                    id="explorer-size",
                                    multi=False,
                                    options=list_to_dropdown_options(all_columns),
                                    placeholder="Marker size",
                                    value=all_columns[3],
                                ),
                                dcc.Dropdown(
                                    id="explorer-facet-row",
                                    multi=False,
                                    options=list_to_dropdown_options(all_columns),
                                    placeholder="Facet row",
                                    value=None,
                                ),
                                dcc.Dropdown(
                                    id="explorer-facet-col",
                                    multi=False,
                                    options=list_to_dropdown_options(all_columns),
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
                            ]
                        ),
                    ]
                ),
            ]
        ),
    ]
)
