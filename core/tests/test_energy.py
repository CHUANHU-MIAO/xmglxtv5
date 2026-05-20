import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.energy.calculator import (
    calculate_equivalent_tce,
    calculate_equivalent_val_tce,
    calculate_annual_cost,
    calculate_energy_item_tce,
    calculate_total_energy,
    calculate_energy_benchmarks,
    calculate_electricity_load,
)
from core.energy.factors import (
    ENERGY_FACTORS,
    get_factor,
    list_factors,
)


class TestEnergyFactors(unittest.TestCase):
    def test_get_factor_exists(self):
        factor = get_factor('电力')
        self.assertIsNotNone(factor)
        self.assertEqual(factor['unit'], '万kWh')

    def test_get_factor_not_exists(self):
        factor = get_factor('不存在')
        self.assertIsNone(factor)

    def test_list_factors(self):
        factors = list_factors()
        self.assertIn('电力', factors)
        self.assertIn('原煤', factors)
        self.assertIn('天然气', factors)

    def test_factor_values(self):
        factor = get_factor('电力')
        self.assertAlmostEqual(factor['equivalent_coef'], 1.229)
        self.assertAlmostEqual(factor['equivalent_coef_val'], 3.015)


class TestCalculateEquivalentTce(unittest.TestCase):
    def test_calculate(self):
        result = calculate_equivalent_tce(100, 1.229)
        self.assertAlmostEqual(result, 122.9)

    def test_zero_qty(self):
        result = calculate_equivalent_tce(0, 1.229)
        self.assertEqual(result, 0)


class TestCalculateEquivalentValTce(unittest.TestCase):
    def test_calculate(self):
        result = calculate_equivalent_val_tce(100, 3.015)
        self.assertAlmostEqual(result, 301.5)


class TestCalculateAnnualCost(unittest.TestCase):
    def test_calculate(self):
        result = calculate_annual_cost(100, 0.5)
        self.assertAlmostEqual(result, 0.005)

    def test_large_values(self):
        result = calculate_annual_cost(1000000, 0.8)
        self.assertAlmostEqual(result, 80.0)


class TestCalculateEnergyItemTce(unittest.TestCase):
    def test_with_factor_name(self):
        eq, ev = calculate_energy_item_tce('电力', 100)
        self.assertAlmostEqual(eq, 122.9)
        self.assertAlmostEqual(ev, 301.5)

    def test_with_custom_coef(self):
        eq, ev = calculate_energy_item_tce('电力', 100, equivalent_coef=2.0, equivalent_coef_val=4.0)
        self.assertAlmostEqual(eq, 200.0)
        self.assertAlmostEqual(ev, 400.0)

    def test_unknown_name(self):
        eq, ev = calculate_energy_item_tce('未知能源', 100)
        self.assertEqual(eq, 0)
        self.assertEqual(ev, 0)


class TestCalculateTotalEnergy(unittest.TestCase):
    def test_empty_items(self):
        total_eq, total_ev, total_cost = calculate_total_energy([])
        self.assertEqual(total_eq, 0)
        self.assertEqual(total_ev, 0)
        self.assertEqual(total_cost, 0)

    def test_single_item(self):
        items = [{'name': '电力', 'annual_qty': 100, 'equivalent_coef': 1.229, 'equivalent_coef_val': 3.015, 'unit_price': 0.8, 'include_in_total': True}]
        total_eq, total_ev, total_cost = calculate_total_energy(items)
        self.assertAlmostEqual(total_eq, 122.9)
        self.assertAlmostEqual(total_ev, 301.5)
        self.assertAlmostEqual(total_cost, 0.008)

    def test_multiple_items(self):
        items = [
            {'name': '电力', 'annual_qty': 100, 'equivalent_coef': 1.229, 'equivalent_coef_val': 3.015, 'unit_price': 0.8, 'include_in_total': True},
            {'name': '天然气', 'annual_qty': 10, 'equivalent_coef': 12.143, 'equivalent_coef_val': 12.143, 'unit_price': 3.5, 'include_in_total': True},
        ]
        total_eq, total_ev, total_cost = calculate_total_energy(items)
        self.assertAlmostEqual(total_eq, 122.9 + 121.43)
        self.assertAlmostEqual(total_ev, 301.5 + 121.43)

    def test_utility_excluded(self):
        items = [
            {'name': '电力', 'annual_qty': 100, 'equivalent_coef': 1.229, 'equivalent_coef_val': 3.015, 'unit_price': 0.8, 'include_in_total': True},
            {'name': '水', 'annual_qty': 1000, 'equivalent_coef': 0.0, 'equivalent_coef_val': 0.0857, 'unit_price': 0.005, 'include_in_total': False},
        ]
        total_eq, total_ev, total_cost = calculate_total_energy(items)
        self.assertAlmostEqual(total_eq, 122.9)


class TestCalculateEnergyBenchmarks(unittest.TestCase):
    def test_all_params(self):
        result = calculate_energy_benchmarks(100, 200, 1000, 500, 50)
        self.assertAlmostEqual(result['area_eq'], 100.0)
        self.assertAlmostEqual(result['output_ev'], 0.4)
        self.assertAlmostEqual(result['output_eq'], 0.2)
        self.assertAlmostEqual(result['product_eq'], 2000.0)

    def test_no_area(self):
        result = calculate_energy_benchmarks(100, 200, None, 500, 50)
        self.assertIsNone(result['area_eq'])

    def test_no_output(self):
        result = calculate_energy_benchmarks(100, 200, 1000, None, 50)
        self.assertIsNone(result['output_ev'])
        self.assertIsNone(result['output_eq'])

    def test_no_product(self):
        result = calculate_energy_benchmarks(100, 200, 1000, 500, 0)
        self.assertIsNone(result['product_eq'])


class TestCalculateElectricityLoad(unittest.TestCase):
    def test_calculate(self):
        result = calculate_electricity_load(50, 1000, 0.75, 0.90, 2190)
        self.assertAlmostEqual(result['work_kw'], 50.0)
        self.assertAlmostEqual(result['total_kw'], 50.0)
        self.assertAlmostEqual(result['active_kw'], 37.5)
        self.assertAlmostEqual(result['power_consumption'], 82125.0)

    def test_zero_density(self):
        result = calculate_electricity_load(0, 1000, 0.75, 0.90, 2190)
        self.assertEqual(result['work_kw'], 0)
        self.assertEqual(result['active_kw'], 0)
        self.assertEqual(result['power_consumption'], 0)


if __name__ == '__main__':
    unittest.main()
