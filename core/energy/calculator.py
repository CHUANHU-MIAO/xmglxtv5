import math
from .factors import ENERGY_FACTORS, get_factor


def calculate_equivalent_tce(annual_qty, equivalent_coef):
    return annual_qty * equivalent_coef


def calculate_equivalent_val_tce(annual_qty, equivalent_coef_val):
    return annual_qty * equivalent_coef_val


def calculate_annual_cost(annual_qty, unit_price):
    return annual_qty * unit_price / 10000


def calculate_energy_item_tce(name, annual_qty, equivalent_coef=None, equivalent_coef_val=None):
    factor = get_factor(name)
    if factor:
        eq_coef = equivalent_coef if equivalent_coef is not None else factor['equivalent_coef']
        ev_coef = equivalent_coef_val if equivalent_coef_val is not None else factor.get('equivalent_coef_val', 0)
    else:
        eq_coef = equivalent_coef or 0
        ev_coef = equivalent_coef_val or 0
    eq_tce = calculate_equivalent_tce(annual_qty, eq_coef)
    ev_tce = calculate_equivalent_val_tce(annual_qty, ev_coef)
    return eq_tce, ev_tce


def calculate_total_energy(items):
    total_eq = 0.0
    total_ev = 0.0
    total_cost = 0.0
    for item in items:
        qty = item.get('annual_qty', 0)
        name = item.get('name', '')
        eq_coef = item.get('equivalent_coef', 0)
        ev_coef = item.get('equivalent_coef_val', 0)
        price = item.get('unit_price', 0)
        include = item.get('include_in_total', True)
        eq_tce, ev_tce = calculate_energy_item_tce(name, qty, eq_coef, ev_coef)
        if include:
            total_eq += eq_tce
            total_ev += ev_tce
        total_cost += calculate_annual_cost(qty, price)
    return total_eq, total_ev, total_cost


def calculate_energy_benchmarks(total_eq, total_ev, area, annual_output, product_qty):
    result = {}
    if area and area > 0:
        result['area_eq'] = total_eq * 1000 / area
    else:
        result['area_eq'] = None
    if annual_output and annual_output > 0:
        result['output_ev'] = total_ev / annual_output
        result['output_eq'] = total_eq / annual_output
    else:
        result['output_ev'] = None
        result['output_eq'] = None
    if product_qty and product_qty > 0 and total_eq > 0:
        result['product_eq'] = total_eq * 1000 / product_qty
    else:
        result['product_eq'] = None
    return result


def calculate_electricity_load(density, density_qty, kc, cos_phi, annual_hours):
    work_kw = density * density_qty / 1000
    total_kw = work_kw
    tg_phi = (math.sin(math.acos(min(cos_phi, 0.999))) / cos_phi) if cos_phi > 0 else 0
    active_kw = total_kw * kc
    reactive_kvar = active_kw * tg_phi
    apparent_kva = active_kw / cos_phi if cos_phi > 0 else 0
    power_consumption = active_kw * annual_hours
    return {
        'work_kw': work_kw,
        'total_kw': total_kw,
        'tg_phi': tg_phi,
        'active_kw': active_kw,
        'reactive_kvar': reactive_kvar,
        'apparent_kva': apparent_kva,
        'power_consumption': power_consumption,
        'annual_hours': annual_hours,
    }
