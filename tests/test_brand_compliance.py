"""Regression tests based on actual 16 October Lakhotia generated copy."""
import unittest
from engine import verify

PHONE="+91 74500 08999"
WEB="www.lakhotiaindustrialcomplex.com"

def c(headline,caption):
    return [{'option':1,'headline':headline,'subheadline':'Industrial planning',
             'caption':caption+' '+PHONE+' '+WEB,
             'cta':'Request consultation','pillar':'Industrial growth'}]

class LakhotiaBrandComplianceTests(unittest.TestCase):
    def check(self,headline,caption):
        return verify(c(headline,caption))[0]
    def test_blocks_real_ready_now_error(self):
        result=self.check("Expand with 1,000 Bighas Ready Now",
                          "1,000 bighas under development and 2,500+ bighas planned expansion.")
        self.assertFalse(result['passed'])
        self.assertTrue(any('readiness' in issue for issue in result['issues']))
    def test_blocks_unqualified_current_area(self):
        self.assertFalse(self.check("Your next move","Explore 1,000 bighas available today.")['passed'])
    def test_blocks_superlatives(self):
        for phrase in ("Prime Industrial Land", "Seamless Connectivity"):
            with self.subTest(phrase=phrase):
                self.assertFalse(self.check(phrase,"Industrial land planning in Howrah.")['passed'])
    def test_blocks_outdated_claim(self):
        self.assertFalse(self.check("Industrial land","800 bighas under development.")['passed'])
    def test_accepts_factual_qualified_copy(self):
        result=self.check("Industrial land planned for your next expansion",
             "Lakhotia Industrial Complex on Ranihati–Amta Road, Howrah: 1,000 bighas under development, with 2,500+ bighas planned expansion. Approximately 4 km from NH-16.")
        self.assertTrue(result['passed'],result['issues'])
    def test_no_arbitrary_area_claim(self):
        self.assertFalse(self.check("Ready to operate","Industrial expansion planning.")['passed'])

if __name__=="__main__":unittest.main()
