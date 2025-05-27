import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from dash.dependencies import Input, Output, ALL, State
from datetime import datetime as dt
from dash import dcc, html
from django.templatetags.static import static
from django_plotly_dash import DjangoDash

import numpy as np
from . import components

from dash import _dash_renderer

_dash_renderer._set_react_version("18.2.0")
dashstyle_url = static('assets/css/dashstyle.css')
fonts_url = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css"

app = DjangoDash('Workflow', external_stylesheets=[fonts_url, dbc.themes.BOOTSTRAP, dashstyle_url] + dmc.styles.ALL)


# ###### Layout Components ######

# -- Workflow Card (Left) --

workflow_card = dbc.Card([

    # Header. Selection.
    dbc.CardHeader(
        "Work Flow",
        style={
            'textAlign': 'center',
            "background-color": "#2B3A67",
            "color": "white",
        }
    ),

    # Body (White area below)
    dbc.CardBody([
        html.Div([components.processing_step(0)],id='output-workflow-body')
    ]),
])

# -- Status Card (Right) --

status_card = dbc.Card([

    # Header. Selection.
    dbc.CardHeader(
        "Status",
        style={
            'textAlign': 'center',
            "background-color": "#2B3A67",
            "color": "white",
        }
    ),

    # Body (White area below)
    dbc.CardBody([
        html.Div([],id='output-status-body')
    ]),
])


# ###### LAYOUT #######

app.layout = dbc.Container(
    fluid='xxl',
    children=[
        # Non-rendered components
        dcc.Store(id="store-main"),

        # Rendered Components
        dbc.Row([
            dbc.Col(workflow_card, lg=6, md=6, sm=12, class_name="h-100 mb-3", ),
            dbc.Col(status_card, lg=6, md=6, sm=12, class_name="h-100 mb-3", ),
        ],
            class_name="align-items-stretch",
        ),
    ],
    className="h-100 d-flex flex-column",
)


# ###### CALLBACKS ######

# Cache current step number
@app.callback(
    Output("store-main", "data"),
    Input({"type": "input-processing-button", "index": ALL}, "n_clicks"),
)
def update_step(n_clicks):
    if n_clicks[0]!=None:
        print(n_clicks)
        n_buttons_pressed = int(np.sum(np.array(n_clicks)>0))
        return {'current_step':n_buttons_pressed}

# Deliver cache number to 
@app.callback(
    Output("output-status-body", "children"),
    Input("store-main", "data"),
)
def status_output(data):
    if data:
        return [components.status_step(data['current_step'])]



@app.callback(
    Output("output-processing-body", "children"),
    Input({"type": "input-status-button", "index": ALL}, "n_clicks"),
    Input("store-main", "data"),
)
def processing_output(n_clicks, data):
    if data:
        current_step = data['current_step']
    else:
        current_step = 0
    if n_clicks:
        if n_click[data[current_step]] > 0:

            processing_content = [components.processing_step(i) for i in range(current_step+2)]

            return [processing_content]
