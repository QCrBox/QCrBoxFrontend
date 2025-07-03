'''Plotly App Config

Plotly App configuration and layouts
for QCrBox Frontend

'''
from dash import html
from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

from django_plotly_dash import DjangoDash

from . import graphs
from .. import models

app = DjangoDash('DataHistoryPanel')

app.layout = dbc.Container(
    fluid='xxl',

    children=[
        # Non-rendered components; using titles of empty divs as makeshift storage
        html.Div(id='init_pk', title=''),
        html.Div(id='pk', title=''),

        # Rendered components
        html.Div(id='tree-container', children=[]),
])

@app.callback(
    Output('pk', 'title'),
    Input('tree-plot', 'clickData'))
def get_seed_from_click_data(clickData):
    '''Callback to detect the user clicking a datapoint in the tree plot and
    cache the pk of the relevant dataset in local de facto storage

    '''

    if not clickData:
        return None
    seed_pk = clickData['points'][0]['customdata']
    return seed_pk

@app.callback(
    Output('tree-container', 'children'),
    Input('pk', 'title'),
    Input('init_pk', 'title'))
def display_data_for_seed(seed_data, init_seed):
    '''Callback to detect changes in local storage and update the graph based
    on the new seed data pk.  Includes a failsafe; if the storage does not
    contain a valid pk (i.e. on first loading this dashboard), instead load
    the plot for the default pk value passed in django context via the view
    method.

    '''

    if not seed_data:
        seed_data=init_seed
    return graphs.tree_plot(models.FileMetaData.objects.get(pk=int(seed_data)))
