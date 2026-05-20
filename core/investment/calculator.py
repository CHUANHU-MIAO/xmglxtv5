def linear_interpolate(table, x):
    if not table:
        return 0
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        x1, y1 = table[i]
        x2, y2 = table[i + 1]
        if x1 <= x <= x2:
            if x2 == x1:
                return y1
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return table[-1][1]

def calculate_project_management_fee(engineering_total):
    wan = engineering_total / 10000
    table = [
        (0, 0.020),
        (1000, 0.020),
        (3000, 0.015),
        (5000, 0.012),
        (10000, 0.010),
    ]
    if wan > 10000:
        rate = 0.008
    else:
        rate = linear_interpolate(table, wan)
    return engineering_total * rate

def calculate_design_fee(engineering_total):
    wan = engineering_total / 10000
    table = [
        (200, 9.0),
        (500, 20.9),
        (1000, 38.8),
        (3000, 103.8),
        (5000, 163.9),
        (8000, 249.6),
        (10000, 304.8),
        (20000, 566.8),
        (50000, 1302.7),
    ]
    return linear_interpolate(table, wan) * 10000

def calculate_survey_fee(building_area, base_rate=15):
    return building_area * base_rate

def calculate_construction_prep_fee(engineering_total, rate=0.005):
    return engineering_total * rate

def calculate_consultation_fee(engineering_total):
    wan = engineering_total / 10000
    table = [
        (0, 0),
        (500, 5.0),
        (1000, 6.5),
        (3000, 13.0),
        (5000, 20.0),
        (10000, 39.0),
        (50000, 95.0),
    ]
    return linear_interpolate(table, wan) * 10000

def calculate_drawing_review_fee(survey_fee, design_fee, rate=0.065):
    return (survey_fee + design_fee) * rate

def calculate_cost_consulting_fee(engineering_total, rate=0.01):
    return engineering_total * rate

def calculate_bidding_agent_fee(engineering_total):
    wan = engineering_total / 10000
    table = [
        (0, 0.010),
        (100, 0.010),
        (500, 0.007),
        (1000, 0.0055),
        (5000, 0.0035),
        (10000, 0.002),
    ]
    if wan > 10000:
        rate = 0.0005
    else:
        rate = linear_interpolate(table, wan)
    return engineering_total * rate

def calculate_supervision_fee(engineering_total):
    wan = engineering_total / 10000
    table = [
        (0, 0),
        (500, 16.5),
        (1000, 30.1),
        (3000, 78.1),
        (5000, 120.8),
        (8000, 181.0),
        (10000, 218.6),
    ]
    return linear_interpolate(table, wan) * 10000

def calculate_insurance_fee(engineering_total, rate=0.006):
    return engineering_total * rate

def calculate_final_settlement_fee(engineering_total, rate=0.003):
    return engineering_total * rate

def calculate_infrastructure_fee(area_or_cost, base_rate=0.012):
    return area_or_cost * base_rate

def calculate_air_defense_fee(area, base_standard=50):
    return area * base_standard

def calculate_all(engineering_total, building_area):
    management_fee = calculate_project_management_fee(engineering_total)
    design_fee = calculate_design_fee(engineering_total)
    survey_fee = calculate_survey_fee(building_area)
    construction_prep_fee = calculate_construction_prep_fee(engineering_total)
    consultation_fee = calculate_consultation_fee(engineering_total)
    drawing_review_fee = calculate_drawing_review_fee(survey_fee, design_fee)
    cost_consulting_fee = calculate_cost_consulting_fee(engineering_total)
    bidding_agent_fee = calculate_bidding_agent_fee(engineering_total)
    supervision_fee = calculate_supervision_fee(engineering_total)
    insurance_fee = calculate_insurance_fee(engineering_total)
    final_settlement_fee = calculate_final_settlement_fee(engineering_total)
    infrastructure_fee = calculate_infrastructure_fee(building_area)
    air_defense_fee = calculate_air_defense_fee(building_area)
    return {
        'project_management_fee': management_fee,
        'design_fee': design_fee,
        'survey_fee': survey_fee,
        'construction_prep_fee': construction_prep_fee,
        'consultation_fee': consultation_fee,
        'drawing_review_fee': drawing_review_fee,
        'cost_consulting_fee': cost_consulting_fee,
        'bidding_agent_fee': bidding_agent_fee,
        'supervision_fee': supervision_fee,
        'insurance_fee': insurance_fee,
        'final_settlement_fee': final_settlement_fee,
        'infrastructure_fee': infrastructure_fee,
        'air_defense_fee': air_defense_fee,
    }