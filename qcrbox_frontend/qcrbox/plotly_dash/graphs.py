'''Plotly Graphs

A module to store methods for creating plots to be included as part of a
Plotly Dash app in the QCrBox Frontend

'''

import plotly.express as px
import plotly.graph_objects as go

from dash import dcc

from .. import models

linestyle = {'color' : 'rgba(0, 0, 0, 0.2)'}

def tree_plot(seed_dataset):
    '''The main Tree Plot for the Tree Dashboard'''

    # Plot the seed
    fig = px.scatter()

    fig.add_trace(go.Scatter(
        x=[0],
        y=[0],
        marker={'color':'red','size': 19},
        hovertemplate=seed_dataset.display_filename,
        name='(Current Selection)',
        customdata=(seed_dataset.pk,)
    ))

    # Plot ancestors
    def plot_ancestors(fig, dataset, current_layer=0):

        try:
            prev_process = models.ProcessStep.objects.get(outfile=dataset)
        except models.ProcessStep.DoesNotExist:
            prev_process = None

        if prev_process:
            ancestor = prev_process.infile

            # Plot point for ancestor
            fig.add_trace(go.Scatter(
                x=[0],
                y=[current_layer+1],
                marker={'color':'blue','size': 15},
                name='',
                hovertemplate=ancestor.display_filename,
                customdata=(ancestor.pk,)
            ))

            # Plot connecting line
            fig.add_trace(go.Scatter(
                x=[0, 0],
                y=[current_layer, current_layer+1],
                mode='lines',
                line=linestyle,
                hovertemplate='',
                zorder=-1,
            ))

            plot_ancestors(fig, ancestor, current_layer=current_layer+1)

        return fig

    fig = plot_ancestors(fig, seed_dataset)

    def plot_descendants(fig, dataset, current_layer=0, x_offset=0, x_width=100):

        post_processes = models.ProcessStep.objects.filter(infile=dataset)
        descendant_pks = list(post_processes.values_list('outfile', flat=True))

        n_children = len(descendant_pks)

        # Indexer to calculate horizontal positioning of each child
        i = 1

        for descendant_pk in descendant_pks:

            descendant = models.FileMetaData.objects.get(pk=descendant_pk)

            # Ensure that the points for each child are reasonably spaced,
            # while still vaguely below their parent
            h_pos = x_offset - (x_width / 2.) + ((i / (n_children + 1)) * x_width )

            # Plot point for descendant
            fig.add_trace(go.Scatter(
                x=[h_pos],
                y=[current_layer-1],
                marker={'color':'blue','size': 15},
                name='',
                hovertemplate=descendant.display_filename,
                customdata=(descendant.pk,)
            ))

            # Plot connecting line
            fig.add_trace(go.Scatter(
                x=[x_offset, h_pos],
                y=[current_layer, current_layer-1],
                mode='lines',
                line=linestyle,
                hovertemplate='',
                zorder=-1,
            ))

            plot_descendants(
                fig,
                descendant,
                current_layer=current_layer-1,
                x_offset=h_pos,
                x_width=x_width/n_children
            )

            i+=1

        return fig

    fig = plot_descendants(fig, seed_dataset)

    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None,
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        xaxis_showticklabels=False,
        yaxis_showticklabels=False,
        xaxis_zeroline=False,
        yaxis_zeroline=False,
        showlegend=False,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
    )

    graph_object = dcc.Graph(
        figure=fig,
        style={
            'width': '100%',
            'height': '100%;',
        },
        id='tree-plot',
    )

    return graph_object
