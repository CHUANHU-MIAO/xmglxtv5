import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.finance.calculator import (
    calculate_yearly_debt_service_equal_principal,
    calculate_yearly_debt_service_equal_installment,
    calculate_yearly_debt_service_lump_sum,
    calculate_debt_service_schedule,
    calculate_npv,
    calculate_irr,
    calculate_payback_period,
    calculate_coverage_ratio,
    calculate_total_debt_service,
    calculate_revenue_projection,
    calculate_profit,
    calculate_sensitivity,
)


class TestDebtServiceEqualPrincipal(unittest.TestCase):
    def test_basic(self):
        schedule = calculate_yearly_debt_service_equal_principal(1000, 0.05, 5, 2024)
        self.assertEqual(len(schedule), 5)
        self.assertEqual(schedule[0]['year'], 2024)
        self.assertAlmostEqual(schedule[0]['principal'], 200)
        self.assertAlmostEqual(schedule[0]['interest'], 50)
        self.assertAlmostEqual(schedule[0]['total'], 250)
        self.assertAlmostEqual(schedule[4]['principal'], 200)
        self.assertAlmostEqual(schedule[4]['interest'], 10)
        self.assertAlmostEqual(schedule[4]['total'], 210)


class TestDebtServiceEqualInstallment(unittest.TestCase):
    def test_basic(self):
        schedule = calculate_yearly_debt_service_equal_installment(1000, 0.05, 5, 2024)
        self.assertEqual(len(schedule), 5)
        self.assertEqual(schedule[0]['year'], 2024)
        self.assertAlmostEqual(schedule[0]['principal'], 180.9748, delta=0.01)
        self.assertAlmostEqual(schedule[0]['interest'], 50, delta=0.01)
        self.assertAlmostEqual(schedule[-1]['remaining'], 0, delta=0.1)

    def test_zero_rate(self):
        schedule = calculate_yearly_debt_service_equal_installment(1000, 0, 5, 2024)
        self.assertAlmostEqual(schedule[0]['principal'], 200)
        self.assertAlmostEqual(schedule[0]['interest'], 0)


class TestDebtServiceLumpSum(unittest.TestCase):
    def test_basic(self):
        schedule = calculate_yearly_debt_service_lump_sum(1000, 0.05, 5, 2024)
        self.assertEqual(len(schedule), 5)
        self.assertEqual(schedule[0]['principal'], 0)
        self.assertAlmostEqual(schedule[0]['interest'], 50)
        self.assertEqual(schedule[4]['principal'], 1000)
        self.assertAlmostEqual(schedule[4]['interest'], 50)
        self.assertAlmostEqual(schedule[4]['total'], 1050)


class TestCalculateDebtServiceSchedule(unittest.TestCase):
    def test_equal_principal(self):
        schedule = calculate_debt_service_schedule(1000, 0.05, 5, 2024, 'equal-principal')
        self.assertEqual(len(schedule), 5)

    def test_equal_installment(self):
        schedule = calculate_debt_service_schedule(1000, 0.05, 5, 2024, 'equal-installment')
        self.assertEqual(len(schedule), 5)

    def test_lump_sum(self):
        schedule = calculate_debt_service_schedule(1000, 0.05, 5, 2024, 'lump-sum')
        self.assertEqual(len(schedule), 5)

    def test_unknown_method(self):
        schedule = calculate_debt_service_schedule(1000, 0.05, 5, 2024, 'unknown')
        self.assertEqual(len(schedule), 5)


class TestNPV(unittest.TestCase):
    def test_positive_npv(self):
        cash_flows = [-1000, 300, 400, 500, 200]
        npv = calculate_npv(cash_flows, 0.1)
        self.assertGreater(npv, 0)

    def test_zero_discount_rate(self):
        cash_flows = [-1000, 300, 400, 300]
        npv = calculate_npv(cash_flows, 0)
        self.assertAlmostEqual(npv, 0)

    def test_single_cash_flow(self):
        npv = calculate_npv([100], 0.1)
        self.assertAlmostEqual(npv, 100)


class TestIRR(unittest.TestCase):
    def test_basic_irr(self):
        cash_flows = [-1000, 300, 400, 500, 200]
        irr = calculate_irr(cash_flows)
        self.assertGreater(irr, 0)

    def test_irr_consistency(self):
        cash_flows = [-1000, 500, 400, 300]
        irr = calculate_irr(cash_flows)
        npv = calculate_npv(cash_flows, irr)
        self.assertAlmostEqual(npv, 0, delta=0.1)


class TestPaybackPeriod(unittest.TestCase):
    def test_exact_payback(self):
        cash_flows = [-1000, 500, 500]
        period = calculate_payback_period(cash_flows)
        self.assertEqual(period, 2.0)

    def test_partial_payback(self):
        cash_flows = [-1000, 400, 400, 400]
        period = calculate_payback_period(cash_flows)
        self.assertAlmostEqual(period, 2.5, delta=0.1)

    def test_no_payback(self):
        cash_flows = [-1000, 100, 100, 100]
        period = calculate_payback_period(cash_flows)
        self.assertIsNone(period)


class TestCoverageRatio(unittest.TestCase):
    def test_basic(self):
        ratio = calculate_coverage_ratio(500, 400)
        self.assertAlmostEqual(ratio, 1.25)

    def test_zero_debt_service(self):
        ratio = calculate_coverage_ratio(500, 0)
        self.assertIsNone(ratio)


class TestTotalDebtService(unittest.TestCase):
    def test_basic(self):
        schedule = [{'principal': 200, 'interest': 50, 'total': 250},
                     {'principal': 200, 'interest': 40, 'total': 240}]
        tp, ti, ttotal = calculate_total_debt_service(schedule)
        self.assertAlmostEqual(tp, 400)
        self.assertAlmostEqual(ti, 90)
        self.assertAlmostEqual(ttotal, 490)


class TestRevenueProjection(unittest.TestCase):
    def test_no_growth(self):
        projection = calculate_revenue_projection(100, 0, 5)
        self.assertEqual(len(projection), 5)
        for v in projection:
            self.assertAlmostEqual(v, 100)

    def test_with_growth(self):
        projection = calculate_revenue_projection(100, 0.1, 3)
        self.assertAlmostEqual(projection[0], 100)
        self.assertAlmostEqual(projection[1], 110)
        self.assertAlmostEqual(projection[2], 121)


class TestCalculateProfit(unittest.TestCase):
    def test_basic(self):
        result = calculate_profit(1000, 600, 50, 100, 50)
        self.assertAlmostEqual(result['operating_profit'], 350)
        self.assertAlmostEqual(result['total_profit'], 200)
        self.assertAlmostEqual(result['net_profit'], 200)


class TestCalculateSensitivity(unittest.TestCase):
    def test_basic(self):
        result = calculate_sensitivity(100, 0.1, 0.1, 0.05)
        self.assertAlmostEqual(result['npv'], 105)


if __name__ == '__main__':
    unittest.main()
