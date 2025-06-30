'''Template tag to allow getting an attribute of an object dynamically
from a string name within a Django HTML template'''

from django import template

REGISTER = template.Library()

@REGISTER.filter(name='getattribute')
def getattribute(value, arg):
    '''Template tag configuration'''

    # Allow for seeking within child objects using standard django parsing
    chain = arg.split('__')

    for arg_att in chain:
        if hasattr(value, str(arg_att)):
            value = getattr(value, arg_att)
        elif hasattr(value, 'has_key') and value.has_key(arg_att):
            value = value[arg_att]
        else:
            return ''

    return value
