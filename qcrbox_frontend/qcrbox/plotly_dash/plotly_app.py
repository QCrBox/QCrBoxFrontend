'''Plotly App Config

Plotly App configuration and layouts
for QCrBox Frontend

'''

from dash import html

from django_plotly_dash import DjangoDash

from . import graphs

app = DjangoDash('SimpleExample')

app.layout = html.Div([
    graphs.tree_plot()

])
