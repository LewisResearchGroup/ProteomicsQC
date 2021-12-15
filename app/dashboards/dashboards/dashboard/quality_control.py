import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt

try:
    from .tools import list_to_dropdown_options
    from . import tools as T
except:
    from tools import list_to_dropdown_options
    import tools as T


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
            [html.P(["x-Axis:", dcc.Dropdown(id="x", options=x_options)])],
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
