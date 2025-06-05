from django import template
from django.conf import settings

register = template.Library()

@register.filter(name='getmtmattribute')
def getattribute(value, arg):
    """Gets an many-to-many handler attribute of an object dynamically from a string name
       and renders it in a human-readable way."""

    # Allow for seeking within child objects using standard django parsing
    chain=arg.split('__')

    for arg in chain:
        if hasattr(value, str(arg)):
            value=getattr(value, arg)
        elif hasattr(value, 'has_key') and value.has_key(arg):
            value=value[arg]
        else:
            return ''

    names = []

    try:
        for i in value.all():
        	names.append(str(i))
    except AttributeError:
    	# If final value does not have an all() method it is not a mtmhandler
    	return ''

    names.sort()

    return ', '.join(names)
