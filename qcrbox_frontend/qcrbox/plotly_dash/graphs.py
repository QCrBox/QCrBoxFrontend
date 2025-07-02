'''Plotly Graphs

A module to store methods for creating plots to be included as part of a
Plotly Dash app in the QCrBox Frontend

'''

import plotly.express as px

from dash import dcc

def tree_plot():
    '''The main Tree Plot for the Tree Dashboard'''

    ##### PLACEHOLDER #####

    fig = px.bar(x=['1', '2', '3'], y=[1, 2, 3])

    graph_component = dcc.Graph(
        figure=fig,
        style={
            'width': '100%',
            'height': '100%;',
        }
    )

    return graph_component
