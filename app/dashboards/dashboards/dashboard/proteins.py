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



plot_columns = ['Peptide counts (all)',
       'Peptide counts (razor+unique)', 'Peptide counts (unique)',
       'Number of proteins', 'Sequence coverage [%]',
       'Unique + razor sequence coverage [%]', 'Unique sequence coverage [%]',
       'Score', 'Reporter intensity corrected', 
       'Reporter intensity corrected (normalized)']

layout = html.Div([

    html.Div(id='protein-table-div', children=[ dt.DataTable(id='protein-table') ], 
            style={'margin-top': '1.5em'}),

    dcc.Dropdown(id='protein-plot-column', multi=False, options=list_to_dropdown_options(plot_columns), 
                placeholder='Select data columns', value='Peptide counts (razor+unique)', 
                style={'width': '100%', 'max-width': '100%'}),

    dcc.Loading([ 
        html.Div(style={'min-width': 400}),
        dcc.Graph(id="protein-figure", config=T.gen_figure_config(filename='protein-groups')),
    ])
])