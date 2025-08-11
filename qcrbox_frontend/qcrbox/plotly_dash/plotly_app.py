'''Plotly App Config

Plotly App configuration and layouts
for QCrBox Frontend

'''
import logging

from dash import html, _dash_renderer
from dash.dependencies import Input, Output
from django.templatetags.static import static

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from django_plotly_dash import DjangoDash

from qcrbox import models
from qcrbox.plotly_dash import graphs

_dash_renderer._set_react_version("18.2.0")
DASHSTYLE_URL = static('assets/css/dashstyle.css')
FONTS_URL = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css"

LOGGER = logging.getLogger(__name__)

app = DjangoDash(
    'DataHistoryPanel',
    external_stylesheets=[FONTS_URL, dbc.themes.BOOTSTRAP, DASHSTYLE_URL] + dmc.styles.ALL,
)


# //==================================================\\
# ||                    TREE CARD                     ||
# \\==================================================//

tree_card = dbc.Card(
    [
        dbc.CardHeader(
            'History',
            id='history-box-title',
            class_name='text-center',
            style={'background-color': '#d4d4d4', 'color': 'black', },
        ),
        dbc.CardBody([html.Div(id='tree-container', children=[])])
    ],
    style={'height':'100%'}
)


# //==================================================\\
# ||                   INFOBOX CARD                   ||
# \\==================================================//

infobox_card = dbc.Card(
    [
        dbc.CardHeader(
            'Information',
            id="data-display-title",
            class_name="text-center",
            style={"background-color": "#d4d4d4", "color": "black", },
        ),
        dbc.CardBody([html.Div(id='infobox-container', children=[])]),
    ],
    style={'height':'100%'},
)


# //==================================================\\
# ||                    APP LAYOUT                     ||
# \\==================================================//

app.layout = dbc.Container(
    fluid='xxl',

    children=[
        # Non-rendered components; using titles of empty divs as makeshift storage
        html.Div(id='init_pk', title=''),
        html.Div(id='pk', title=''),

        # Rendered components

        dbc.Row(
            [
                dbc.Col(tree_card, lg=6, md=6, sm=12, class_name="h-100 mb-3", ),
                dbc.Col(infobox_card, lg=6, md=6, sm=12, class_name="h-100 mb-3", ),
            ],
            class_name="align-items-stretch",
        ),
])


# //==================================================\\
# ||                    CALLBACKS                     ||
# \\==================================================//

@app.callback(
    Output('pk', 'title'),
    Input('tree-plot', 'clickData'))
def get_seed_from_click_data(click_data):
    '''Callback to detect the user clicking a datapoint in the tree plot and
    cache the pk of the relevant dataset in local de facto storage

    '''

    if not click_data:
        return None
    seed_pk = click_data['points'][0]['customdata']
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
    LOGGER.info('Generating tree plot for dataset pk=%s',seed_data)
    metadata_objs = models.FileMetaData.objects                         # pylint: disable=no-member
    return graphs.tree_plot(metadata_objs.get(pk=int(seed_data)))

@app.callback(
    Output('infobox-container', 'children'),
    Input('pk', 'title'),
    Input('init_pk', 'title'))
def display_infobox_for_seed(seed_data, init_seed):
    '''Callback to detect changes in local storage and update the infobox
    based on the new seed data pk.  Includes a failsafe; if the storage does
    not contain a valid pk (i.e. on first loading this dashboard), instead
    load the infobox for the default pk value passed in django context via the
    view method.

    '''

    if not seed_data:
        seed_data=init_seed
    metadata_objs = models.FileMetaData.objects                         # pylint: disable=no-member
    return graphs.infobox(metadata_objs.get(pk=int(seed_data)))
