import json
from django import template

register = template.Library()

@register.filter
def parse_json(value):
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}