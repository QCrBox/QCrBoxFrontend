from django import template
from django.conf import settings

register = template.Library()

@register.filter(name='getattribute')
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""

    # Allow for seeking within child objects using standard django parsing
    chain=arg.split('__')

    for arg in chain:
        if hasattr(value, str(arg)):
            value=getattr(value, arg)
        elif hasattr(value, 'has_key') and value.has_key(arg):
            value=value[arg]
        else:
            return ''

    return value
