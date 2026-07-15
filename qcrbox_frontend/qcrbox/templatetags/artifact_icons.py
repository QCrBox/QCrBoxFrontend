'''artifact_icons.py: template filter mapping artifact kinds to FontAwesome
icon classes for the workflow pipeline display.'''

from django import template

register = template.Library()

ARTIFACT_ICONS = {
    'text': 'fa-solid fa-file-lines',
    'image': 'fa-solid fa-image',
    'html': 'fa-solid fa-file-code',
    'interactive_structure': 'fa-solid fa-cube',
    'interactive_graph': 'fa-solid fa-chart-line',
}


@register.filter
def artifact_icon(kind):
    '''Return the FontAwesome icon classes for an artifact kind.'''
    return ARTIFACT_ICONS.get(kind, 'fa-solid fa-file')
