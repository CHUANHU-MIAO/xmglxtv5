import math


def calculate_yearly_debt_service_equal_principal(principal, annual_rate, years, start_year):
    annual_principal = principal / years
    schedule = []
    for i in range(years):
        year = start_year + i
        remaining = principal - annual_principal * i
        interest = remaining * annual_rate
        total = annual_principal + interest
        schedule.append({
            'year': year,
            'principal': annual_principal,
            'interest': interest,
            'total': total,
            'remaining': remaining - annual_principal,
        })
    return schedule


def calculate_yearly_debt_service_equal_installment(principal, annual_rate, years, start_year):
    if annual_rate == 0:
        annual_total = principal / years
    else:
        annual_total = principal * annual_rate * (1 + annual_rate) ** years / ((1 + annual_rate) ** years - 1)
    schedule = []
    remaining = principal
    for i in range(years):
        year = start_year + i
        interest = remaining * annual_rate
        principal_paid = annual_total - interest
        remaining -= principal_paid
        schedule.append({
            'year': year,
            'principal': principal_paid,
            'interest': interest,
            'total': annual_total,
            'remaining': max(remaining, 0),
        })
    return schedule


def calculate_yearly_debt_service_lump_sum(principal, annual_rate, years, start_year):
    schedule = []
    for i in range(years):
        year = start_year + i
        is_last = i == years - 1
        interest = principal * annual_rate
        principal_paid = principal if is_last else 0
        total = principal + interest if is_last else interest
        schedule.append({
            'year': year,
            'principal': principal_paid,
            'interest': interest,
            'total': total,
            'remaining': 0 if is_last else principal,
        })
    return schedule


def calculate_debt_service_schedule(principal, annual_rate, years, start_year, method='equal-principal'):
    if method == 'equal-principal':
        return calculate_yearly_debt_service_equal_principal(principal, annual_rate, years, start_year)
    elif method == 'equal-installment':
        return calculate_yearly_debt_service_equal_installment(principal, annual_rate, years, start_year)
    elif method == 'lump-sum':
        return calculate_yearly_debt_service_lump_sum(principal, annual_rate, years, start_year)
    else:
        return calculate_yearly_debt_service_equal_principal(principal, annual_rate, years, start_year)


def calculate_npv(cash_flows, discount_rate):
    npv = 0.0
    for i, cf in enumerate(cash_flows):
        npv += cf / (1 + discount_rate) ** i
    return npv


def calculate_irr(cash_flows, guess=0.1, max_iter=1000, tolerance=1e-7):
    rate = guess
    for _ in range(max_iter):
        npv = 0.0
        dnpv = 0.0
        for i, cf in enumerate(cash_flows):
            npv += cf / (1 + rate) ** i
            dnpv -= i * cf / (1 + rate) ** (i + 1)
        if abs(npv) < tolerance:
            return rate
        if dnpv == 0:
            return rate
        rate -= npv / dnpv
    return rate


def calculate_payback_period(cash_flows):
    cumulative = 0.0
    for i, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0:
            if i == 0:
                return 0
            prev_cumulative = cumulative - cf
            if cf != 0:
                return i - 1 + (-prev_cumulative) / cf
            return i
    return None


def calculate_coverage_ratio(net_income, debt_service):
    if not debt_service or abs(debt_service) < 1e-10:
        return None
    return net_income / debt_service


def calculate_total_debt_service(schedule):
    total_principal = sum(item['principal'] for item in schedule)
    total_interest = sum(item['interest'] for item in schedule)
    total_payment = sum(item['total'] for item in schedule)
    return total_principal, total_interest, total_payment


def calculate_revenue_projection(annual_revenue, growth_rate, years):
    projection = []
    for i in range(years):
        revenue = annual_revenue * (1 + growth_rate) ** i
        projection.append(revenue)
    return projection


def calculate_profit(revenues, costs, taxes, depreciation, amortization):
    operating_profit = revenues - costs - taxes
    total_cost = operating_profit - depreciation - amortization
    net_profit = total_cost
    return {
        'operating_profit': operating_profit,
        'total_profit': total_cost,
        'net_profit': net_profit,
    }


def calculate_sensitivity(base_npv, base_irr, revenue_change, cost_change):
    npv_change = base_npv * (1 + revenue_change - cost_change)
    irr_change = base_irr
    return {
        'npv': npv_change,
        'irr': irr_change,
        'revenue_change': revenue_change,
        'cost_change': cost_change,
    }
