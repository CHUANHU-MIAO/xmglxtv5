import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.investment.calculator import (
    linear_interpolate,
    calculate_project_management_fee,
    calculate_design_fee,
    calculate_survey_fee,
    calculate_construction_prep_fee,
    calculate_consultation_fee,
    calculate_drawing_review_fee,
    calculate_cost_consulting_fee,
    calculate_bidding_agent_fee,
    calculate_supervision_fee,
    calculate_insurance_fee,
    calculate_final_settlement_fee,
    calculate_infrastructure_fee,
    calculate_air_defense_fee,
    calculate_all,
)


class TestLinearInterpolate(unittest.TestCase):
    def test_exact_match(self):
        table = [(0, 0), (100, 100), (200, 200)]
        self.assertEqual(linear_interpolate(table, 100), 100)

    def test_interpolate(self):
        table = [(0, 0), (100, 100), (200, 200)]
        self.assertEqual(linear_interpolate(table, 50), 50)

    def test_below_table(self):
        table = [(100, 100), (200, 200)]
        self.assertEqual(linear_interpolate(table, 50), 100)

    def test_above_table(self):
        table = [(0, 0), (100, 100)]
        self.assertEqual(linear_interpolate(table, 200), 100)

    def test_empty_table(self):
        self.assertEqual(linear_interpolate([], 100), 0)


class TestProjectManagementFee(unittest.TestCase):
    def test_below_1000(self):
        fee = calculate_project_management_fee(5000000)
        self.assertAlmostEqual(fee, 100000, delta=1)

    def test_between_1000_and_3000(self):
        fee = calculate_project_management_fee(20000000)
        expected = 20000000 * 0.0175
        self.assertAlmostEqual(fee, expected, delta=1)

    def test_at_3000(self):
        fee = calculate_project_management_fee(30000000)
        expected = 30000000 * 0.015
        self.assertAlmostEqual(fee, expected, delta=1)

    def test_above_10000(self):
        fee = calculate_project_management_fee(150000000)
        expected = 150000000 * 0.008
        self.assertAlmostEqual(fee, expected, delta=1)


class TestDesignFee(unittest.TestCase):
    def test_at_200(self):
        fee = calculate_design_fee(2000000)
        self.assertAlmostEqual(fee, 90000, delta=1)

    def test_at_500(self):
        fee = calculate_design_fee(5000000)
        self.assertAlmostEqual(fee, 209000, delta=1)

    def test_interpolate_between_200_and_500(self):
        fee = calculate_design_fee(3500000)
        expected = 90000 + (209000 - 90000) * (350 - 200) / (500 - 200)
        self.assertAlmostEqual(fee, expected, delta=1)

    def test_above_50000(self):
        fee = calculate_design_fee(600000000)
        self.assertAlmostEqual(fee, 13027000, delta=1)


class TestSurveyFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_survey_fee(10000)
        self.assertEqual(fee, 150000)

    def test_custom_rate(self):
        fee = calculate_survey_fee(10000, base_rate=20)
        self.assertEqual(fee, 200000)


class TestConstructionPrepFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_construction_prep_fee(100000000)
        self.assertEqual(fee, 500000)

    def test_custom_rate(self):
        fee = calculate_construction_prep_fee(100000000, rate=0.01)
        self.assertEqual(fee, 1000000)


class TestConsultationFee(unittest.TestCase):
    def test_at_500(self):
        fee = calculate_consultation_fee(5000000)
        self.assertAlmostEqual(fee, 50000, delta=1)

    def test_at_50000(self):
        fee = calculate_consultation_fee(500000000)
        self.assertAlmostEqual(fee, 950000, delta=1)


class TestDrawingReviewFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_drawing_review_fee(100000, 200000)
        self.assertAlmostEqual(fee, 19500, delta=1)


class TestCostConsultingFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_cost_consulting_fee(100000000)
        self.assertEqual(fee, 1000000)


class TestBiddingAgentFee(unittest.TestCase):
    def test_below_100(self):
        fee = calculate_bidding_agent_fee(500000)
        self.assertAlmostEqual(fee, 5000, delta=1)

    def test_above_10000(self):
        fee = calculate_bidding_agent_fee(200000000)
        expected = 200000000 * 0.0005
        self.assertAlmostEqual(fee, expected, delta=1)


class TestSupervisionFee(unittest.TestCase):
    def test_at_500(self):
        fee = calculate_supervision_fee(5000000)
        self.assertAlmostEqual(fee, 165000, delta=1)

    def test_at_10000(self):
        fee = calculate_supervision_fee(100000000)
        self.assertAlmostEqual(fee, 2186000, delta=1)


class TestInsuranceFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_insurance_fee(100000000)
        self.assertEqual(fee, 600000)


class TestFinalSettlementFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_final_settlement_fee(100000000)
        self.assertEqual(fee, 300000)


class TestInfrastructureFee(unittest.TestCase):
    def test_default_rate(self):
        fee = calculate_infrastructure_fee(50000)
        self.assertEqual(fee, 600)


class TestAirDefenseFee(unittest.TestCase):
    def test_default_standard(self):
        fee = calculate_air_defense_fee(10000)
        self.assertEqual(fee, 500000)


class TestCalculateAll(unittest.TestCase):
    def test_calculate_all_returns_dict(self):
        result = calculate_all(50000000, 10000)
        self.assertIsInstance(result, dict)
        self.assertIn('project_management_fee', result)
        self.assertIn('design_fee', result)
        self.assertIn('survey_fee', result)
        self.assertIn('air_defense_fee', result)

    def test_calculate_all_values(self):
        result = calculate_all(50000000, 10000)
        self.assertGreater(result['project_management_fee'], 0)
        self.assertGreater(result['design_fee'], 0)
        self.assertGreater(result['survey_fee'], 0)
        self.assertEqual(result['survey_fee'], 150000)
        self.assertEqual(result['air_defense_fee'], 500000)


if __name__ == '__main__':
    unittest.main()
