from dash.dependencies import Input, Output, ALL, State
from dash import dcc, html


# Left panel content

def workflow_step(i):
    return html.Button('File:',id={"type": "input-processing-button", "index": i})


# Right panel content

def status_step(i):
    return html.Button('Continue',id={"type": "input-status-button", "index": i})