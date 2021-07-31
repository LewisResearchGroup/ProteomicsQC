import dash_core_components as dcc
import dash_html_components as html 
import dash_bootstrap_components as dbc 
import dash_table as dt

try:
    from .tools import list_to_dropdown_options
    from .config import qc_columns_options, qc_columns_default
    from . import tools as T
except:
    from tools import list_to_dropdown_options
    from config import qc_columns_options, qc_columns_default
    import tools as T


x_options = [dict(label=x, value=x) for x in ['Index', 'RawFile', 'DateAcquired',]]

layout = html.Div([

    html.P(["Choose columns:", dcc.Dropdown(id='qc-table-columns', multi=True, 
                                            options=list_to_dropdown_options(qc_columns_options), 
                                            placeholder='Select data columns', 
                                            value=qc_columns_default,
                                            )]),
    
    html.Button('Update Table Data', id='qc-update-table', className='btn'),

    dcc.Loading([ 
        html.Div(id='qc-table-div', children=[ dt.DataTable(id='qc-table') ], 
                 style={'margin-top': '1.5em', 'minHeight': '400px'}) 
    ]),
    

    # hack to turn off browser autocomplete 
    html.Script(children='document.getElementById("qc-table-columns").getAttribute("autocomplete") = "off";'),

    html.Div([ html.P(["x-Axis:", dcc.Dropdown(id='x', options=x_options)])],
            style={"width": "100%", 'margin': 'auto'}),

    html.Div([html.Button('Refresh Plots', id='refresh-plots', className='btn')],
             style={'margin-bottom': 100}),

    dcc.Loading([ 
        html.Div([
            dcc.Graph(id="qc-figure", style={'max-width': '100%'}),        
    ], style={'textAlign': 'center'})
    ]),
])





