from django import template

register = template.Library()

@register.filter
def split(value, sep="/"):
    """Split string by separator (default '/') and remove empty strings."""
    return [item for item in value.split(sep) if item]

@register.filter
def index(value, index):
    """Get the item at the specified index from a list."""
    try:
        return value[int(index)]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter(name="get_field")
def get_field(form, name):
    """Return bound form field by its name (string) or None if missing."""
    try:
        return form[name]
    except Exception:
        return None

@register.filter(name="get_item")
def get_item(mapping, key):
    """Return mapping[key] or None — used to look up dict values in templates."""
    try:
        return mapping.get(key)
    except (AttributeError, TypeError):
        return None