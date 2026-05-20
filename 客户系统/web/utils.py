def format_number(value):
    if value is None:
        return '0.00'
    try:
        return f'{float(value):.2f}'
    except (ValueError, TypeError):
        return '0.00'


def format_wan(value):
    if value is None:
        return '0.00'
    try:
        v = float(value) / 10000
        return f'{v:.2f}'
    except (ValueError, TypeError):
        return '0.00'
