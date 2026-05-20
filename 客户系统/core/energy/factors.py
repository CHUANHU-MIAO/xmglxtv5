import math

ENERGY_FACTORS = {
    '电力': {
        'unit': '万kWh',
        'equivalent_coef': 1.229,
        'equivalent_note': '当量值: 1.229 tce/万kWh',
        'equivalent_coef_val': 3.015,
        'equivalent_val_note': '等价值: 3.015 tce/万kWh',
        'category': '能源',
    },
    '原煤': {
        'unit': 't',
        'equivalent_coef': 0.7143,
        'equivalent_note': '0.7143 tce/t',
        'equivalent_coef_val': 0.7143,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '洗精煤': {
        'unit': 't',
        'equivalent_coef': 0.9000,
        'equivalent_note': '0.9000 tce/t',
        'equivalent_coef_val': 0.9000,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '焦炭': {
        'unit': 't',
        'equivalent_coef': 0.9714,
        'equivalent_note': '0.9714 tce/t',
        'equivalent_coef_val': 0.9714,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '天然气': {
        'unit': '万m³',
        'equivalent_coef': 12.143,
        'equivalent_note': '12.143 tce/万m³',
        'equivalent_coef_val': 12.143,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '液化天然气': {
        'unit': 't',
        'equivalent_coef': 1.7572,
        'equivalent_note': '1.7572 tce/t',
        'equivalent_coef_val': 1.7572,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '汽油': {
        'unit': 't',
        'equivalent_coef': 1.4714,
        'equivalent_note': '1.4714 tce/t',
        'equivalent_coef_val': 1.4714,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '煤油': {
        'unit': 't',
        'equivalent_coef': 1.4714,
        'equivalent_note': '1.4714 tce/t',
        'equivalent_coef_val': 1.4714,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '柴油': {
        'unit': 't',
        'equivalent_coef': 1.4571,
        'equivalent_note': '1.4571 tce/t',
        'equivalent_coef_val': 1.4571,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '燃料油': {
        'unit': 't',
        'equivalent_coef': 1.4286,
        'equivalent_note': '1.4286 tce/t',
        'equivalent_coef_val': 1.4286,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '液化石油气': {
        'unit': 't',
        'equivalent_coef': 1.7143,
        'equivalent_note': '1.7143 tce/t',
        'equivalent_coef_val': 1.7143,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '热力': {
        'unit': 'GJ',
        'equivalent_coef': 0.0341,
        'equivalent_note': '0.0341 tce/GJ',
        'equivalent_coef_val': 0.0341,
        'equivalent_val_note': '',
        'category': '能源',
    },
    '水': {
        'unit': 't',
        'equivalent_coef': 0.0000,
        'equivalent_note': '',
        'equivalent_coef_val': 0.0857,
        'equivalent_val_note': '等价值: 0.0857 tce/t',
        'category': '耗能工质',
    },
    '压缩空气': {
        'unit': '万m³',
        'equivalent_coef': 0.0000,
        'equivalent_note': '',
        'equivalent_coef_val': 0.4000,
        'equivalent_val_note': '等价值: 0.4000 tce/万m³',
        'category': '耗能工质',
    },
    '二氧化碳': {
        'unit': 't',
        'equivalent_coef': 0.0000,
        'equivalent_note': '',
        'equivalent_coef_val': 0.0000,
        'equivalent_val_note': '',
        'category': '耗能工质',
    },
}


def get_factor(name):
    return ENERGY_FACTORS.get(name)


def list_factors():
    return list(ENERGY_FACTORS.keys())
