from django.template import Library

register=Library()

@register.filter(name='bonus')
def bonus(intval):
    if isinstance(intval, int) and intval>-1:
        return "+"+str(intval)
    if intval is None:
        return "+0"#absent values should be rendered
    return intval
