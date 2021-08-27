import os
import sys
import json
import logging
import requests
import pandas as pd
import dash_table as dt
from dash_table.Format import Format

URL = os.getenv('OMICS_URL', 'http://localhost:8000')

logging.info(f'Dashboard API URL:{URL}', file=sys.stderr)


def list_to_dropdown_options(values):
    return [{'label': v, 'value': v} for v in values]


def table_from_dataframe(df, id='table', row_deletable=True, row_selectable='multi'):
    return dt.DataTable(
        id=id,
        columns=[{'name': i, 'id': i, 'format': Format(precision=2)} for i in df.columns],
        data=df.iloc[::-1].to_dict('records'),
        sort_action='native',
        sort_mode='single',
        row_selectable=row_selectable,
        row_deletable=row_deletable,
        selected_rows=[],
        filter_action='native',
        page_action='native',
        page_current=0,
        page_size=16,
        style_table={'overflowX': 'scroll'},
        export_format='csv',
        export_headers='display',
        merge_duplicate_headers=True,
        style_cell={
            'font_size': '10px', 
            'padding-left': '5em', 
            'padding-right': '5em'}      
        )


def get_projects():
    url = f'{URL}/api/projects'
    try:
        _json = requests.post(url).json()
    except:
        return []
    output = [ {'label': i['name'], 'value': i['slug']} for i in _json]
    return output


def get_pipelines(project):
    url = f'{URL}/api/mq/pipelines'
    headers = {'Content-type': 'application/json'}
    data = json.dumps( dict(project=project) )
    return requests.post(url, data=data, headers=headers).json()


def get_protein_groups(project, pipeline, protein_names=None, columns=None, data_range=None):
    url = f'{URL}/api/mq/protein-groups'
    headers = {'Content-type': 'application/json'}
    data =  json.dumps( dict(project=project, 
                             pipeline=pipeline, 
                             protein_names=protein_names,
                             columns=columns, 
                             data_range=data_range,
                             ) 
            )
    res = requests.post(url, data=data, headers=headers).json()
    return res


def get_protein_names(project, pipeline, add_con=True, add_rev=True,  data_range=None):
    url = f'{URL}/api/mq/protein-names'
    headers = {'Content-type': 'application/json'}
    data =  json.dumps( dict(project=project, 
                             pipeline=pipeline,                             
                             add_con=add_con,
                             data_range=data_range,
                             add_rev=add_rev)
            )
    _json = requests.post(url, data=data, headers=headers).json()
    return _json


def get_qc_data(project, pipeline, columns, data_range=None):
    url = f'{URL}/api/mq/qc-data'
    headers = {'Content-type': 'application/json'}
    data =  json.dumps( dict(project=project, pipeline=pipeline, 
                             columns=columns, data_range=data_range) )
    return requests.post(url, data=data, headers=headers).json()


def gen_figure_config(filename='plot', format='svg', 
        height=None, width=None, scale=None, editable=True):
    config = {
        'toImageButtonOptions': {
            'format': format,
            'filename': filename
            },
        'height': height,
        'width': width,
        'scale': scale,
        'editable': editable
        }
    return config


def gen_tabulator_columns(col_names=None, add_ms_file_col=False, add_color_col=False, 
                          add_peakopt_col=False, add_ms_file_active_col=False,
                          col_width='12px', editor='input'):

    if col_names is None: col_names = []
    else: col_names = list(col_names)

    columns = [
            { "formatter": "rowSelection", "titleFormatter": "rowSelection",           
              "titleFormatterParams": {
                  "rowRange": "active"
              },
              "hozAlign":"center", "headerSort": False, "width":"1px", 'frozen': True}]

    for col in col_names:
        content = { 'title': col, 
                    'field': col, 
                    'headerFilter': True, 
                    'width': col_width, 
                    'editor': editor 
                  }

        columns.append(content)
        
    return columns