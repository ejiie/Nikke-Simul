import math
import unittest
from actual_stats import tcritical

class IndependentIntegrationTests(unittest.TestCase):
    def test_cauchy_df1_closed_form(self):
        self.assertAlmostEqual(tcritical(1),math.tan(.475*math.pi),places=7)

    def test_df2_closed_form(self):
        self.assertAlmostEqual(tcritical(2),math.sqrt(2)*.95/math.sqrt(1-.95**2),places=7)
