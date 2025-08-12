'''Plotly Graphs

A module to store methods for creating plots to be included as part of a
Plotly Dash app in the QCrBox Frontend

'''

import ast

import plotly.express as px
import plotly.graph_objects as go

from django.urls import reverse

from dash import dcc, html

from qcrbox import models, utility

def tree_plot(seed_dataset):
    '''Generate the main Tree Plot for the History Dashboard

    Parameters:
    - seed_dataset(FileMetaData): the FileMetaData model instance
            corresponding to the data being used as the 'seed' for the tree
            plot, i.e. the central node which is labelled as currently
            selected.

    Returns:
    - graph_objects(dcc.Graph): the dash dcc component containing the tree
            plot.

    '''

    # Plotting kwargs common to all 'point' plots
    point_kwargs = {
        'mode':'markers+text',
        'textposition':'bottom center',
        'name':'',
    }

    # Plotting kwargs common to all 'connector' plots
    connector_kwargs = {
        'mode':'lines',
        'line':{'color' : 'rgba(0, 0, 0, 0.2)'},
        'hovertemplate':'',
        'zorder':-1,
        'hoverinfo':'none',
    }

    # Plot the point for the seed dataset.
    fig = px.scatter()

    fig.add_trace(go.Scatter(
        x=[0],
        y=[0],
        marker={'color':'red','size': 19},
        text=seed_dataset.display_filename,
        hovertemplate='Current Selection',
        customdata=(seed_dataset.pk,),
        **point_kwargs,
    ))

    # Plot ancestors
    def plot_ancestors(fig, dataset, current_layer=0):
        '''Recursively find all ancestors of a given dataset and add points
        for them to a tree plot

        Parameters:
        - fig(Figure): Plotly figure object containing the tree plot
        - dataset: The current dataset to find ancestors of
        - current_layer(int, optional): The 'generation' of the current
                dataset being worked on.  The seed data for the tree plot is
                at layer 0, its parent is at layer 1, grandparent is at layer
                2, etc.  Leave this value as the default 0 when calling this
                function, it is used internally to pass information to
                recursive calls.

        Returns:
        - fig(Figure): The annotated Plotly figure object with added
                datapoints for the chosen dataset's ancestors.
        - max_generation(int): The maximum generation found, e.g. +1 for
                parent, +2 for grandparent, etc.

        '''

        # Assume the max generation is the current one unless told otherwise
        max_generation = current_layer

        try:
            process_objs = models.ProcessStep.objects                   # pylint: disable=no-member
            prev_process = process_objs.get(outfile=dataset)
        except models.ProcessStep.DoesNotExist:                         # pylint: disable=no-member
            prev_process = None

        if prev_process:
            ancestor = prev_process.infile

            # Plot point for ancestor
            fig.add_trace(go.Scatter(
                x=[0],
                y=[current_layer + 1],
                marker={'color':'blue','size': 15},
                text=ancestor.display_filename,
                customdata=(ancestor.pk,),
                hovertemplate=f'Go to {ancestor.display_filename}',
                **point_kwargs,
            ))

            # Plot connecting line
            fig.add_trace(go.Scatter(
                x=[0, 0],
                y=[current_layer, current_layer + 1],
                **connector_kwargs,
            ))

            fig, max_generation = plot_ancestors(fig, ancestor, current_layer=current_layer + 1)

        return fig, max_generation

    fig, max_generation = plot_ancestors(fig, seed_dataset)

    def plot_descendants(fig, dataset, current_layer=0, x_offset=0, x_width=100):
        '''Recursively find all descendants of a given dataset and add points
        for them to a tree plot

        Parameters:
        - fig(Figure): Plotly figure object containing the tree plot
        - dataset: The current dataset to find descendants of
        - current_layer(int, optional): The 'generation' of the current
                dataset being worked on.  The seed data for the tree plot is
                at layer 0, its children are at layer -1, grandchildren are at
                layer -2, etc.  Leave this value as the default 0 when calling
                this function, it is used internally to pass information to
                recursive calls.
        - x_offset(int, optional): A parameter to keep track of the horizontal
                position of the parent of the current subtree being worked on.
                Leave this value as the default 0 when calling this function,
                it is used internally to pass information to recursive calls.
        - x_width(int or float, optional): A parameter to keep track of the
                horizontal width available to each subtree.  Used in recursive
                calls to govern horizontal spacing of subtrees.

        Returns:
        - fig(Figure): The annotated Plotly figure object with added
                datapoints for the chosen dataset's descendants.

        '''

        # Assume the max generation is the current one unless told otherwise
        min_generation = current_layer

        process_objs = models.ProcessStep.objects                       # pylint: disable=no-member
        post_processes = process_objs.filter(infile=dataset)
        descendant_pks = list(post_processes.values_list('outfile', flat=True))

        n_children = len(descendant_pks)

        # Indexer to calculate horizontal positioning of each child
        i = 1

        # Track the number of generations of dependents

        for d_pk in descendant_pks:

            descendant = models.FileMetaData.objects.get(pk=d_pk)       # pylint: disable=no-member

            # Ensure that the points for each child are reasonably spaced,
            # while still vaguely below their parent
            h_pos = x_offset - (x_width / 2.) + ((i / (n_children + 1)) * x_width )

            # Plot point for descendant
            fig.add_trace(go.Scatter(
                x=[h_pos],
                y=[current_layer-1],
                marker={'color':'blue','size': 15},
                text=utility.twrap(descendant.display_filename, int(x_width//n_children)),
                customdata=(descendant.pk,),
                hovertemplate=f'Go to {descendant.display_filename}',
                **point_kwargs,
            ))

            # Plot connecting line
            fig.add_trace(go.Scatter(
                x=[x_offset, h_pos, h_pos],
                y=[current_layer, current_layer, current_layer-1],
                **connector_kwargs,
            ))

            fig, end_generation = plot_descendants(
                fig,
                descendant,
                current_layer=current_layer-1,
                x_offset=h_pos,
                x_width=x_width/n_children,
            )

            min_generation = min(min_generation, end_generation)

            i+=1

        return fig, min_generation

    fig, min_generation = plot_descendants(fig, seed_dataset)

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
        margin={'l':0, 'r':0, 't':10, 'b':10},
        autosize=True,
    )

    # Fetch yrange to generate custom y-axis padding
    yrange = max_generation - min_generation

    # Prevent zooming, other plotlyish interactivity
    fig.update_xaxes(range=[-33.4, 33.4])
    fig.update_yaxes(range=[min_generation-(yrange/4), max_generation+(yrange/16)])
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    graph_object = dcc.Graph(
        figure=fig,
        style={
            'width': '100%',
            'height': '100%;',
        },
        id='tree-plot',
        config={'displayModeBar':False},
    )

    return graph_object

def infobox(seed_dataset):

    '''Generate the main Infobox for the History Dashboard

    Parameters:
    - seed_dataset(FileMetaData): the FileMetaData model instance
            corresponding to the metadata set to be displayed in the infobox

    Returns:
    - graph_objects(dcc.Graph): the dash dcc component containing the tree
            plot.

    '''

    def table_row(name, data):
        '''Simple function to generate 2-width html table row'''

        row = html.Tr([
            html.Td(f'{name}\xa0', style={'text-align':'right'}),
            html.Td(data),
        ])

        return row

    # Populate basic info which is always available

    table_contents = [
        html.Tr([
            html.Td([html.H5('Dataset Information')], colSpan=2),
        ]),
        table_row('Filename: ', seed_dataset.display_filename),
        table_row('File type: ', seed_dataset.filetype),
        table_row('Group: ', seed_dataset.group.name),
        table_row('Status: ', 'Available' if seed_dataset.active else 'Deleted'),
        html.Tr([
            html.Td([html.Br(),html.H5('Creation History')], colSpan=2),
        ]),

    ]

    # Fetch creation history based on whether this was uploaded or made
    # from an Interactive Session

    process_objs = models.ProcessStep.objects                           # pylint: disable=no-member
    creation_process = process_objs.filter(outfile=seed_dataset)

    if creation_process.exists():

        process = creation_process.first()
        app = process.command.app.name
        version = process.command.app.version
        command = process.command.name
        parent = process.infile.display_filename
        params = ast.literal_eval(process.parameters)

        # Remove some params which shouldnt be displayed in the table
        for hidden_param in [
            'cif1',
            'input_cif',
            'output_cif_path',
            'output_json_path',
            'output_tsc_path',
        ]:
            params.pop(hidden_param, None)

    else:

        app = html.I('Upload')
        version = '-'
        command = '-'
        parent = '-'
        params = {}

    creation_table_1 = [
        table_row('Application: ', app),
        table_row('Version: ', version),
        table_row('Command: ', command),
        table_row('Parent Dataset: ', parent),
    ]

    creation_table_2 = [
        table_row('User: ', seed_dataset.user.username),
        table_row('Date: ', seed_dataset.creation_time.strftime('%Y-%m-%d')),
        table_row('Time: ', seed_dataset.creation_time.strftime('%H:%M:%S')),
    ]

    params_table = [
        table_row(
            p.replace('_', ' ').title() + ': ',
            v,
        ) for p, v in params.items()
    ]

    table_contents += creation_table_1 + params_table + creation_table_2

    # Create button to launch workflow

    workflow_button = html.A(
        html.Button('Start Workflow'),
        href=reverse('workflow', kwargs={'file_id': seed_dataset.pk}),
        id='workflow-link',
    )

    return [
        html.Table(table_contents), html.Br(), workflow_button]
