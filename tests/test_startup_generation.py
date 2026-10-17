import unittest
from unittest.mock import patch
import startup_generation as g
class ProductionSeedTests(unittest.TestCase):
    def test_factual_three_category_brief_within_api_limit(self):
        self.assertLessEqual(len(g.BRIEF),900)
        for category in ('ARCHITECTURE','HUMAN OPERATIONS','UTILITIES & TECHNOLOGY'):
            self.assertIn(category,g.BRIEF)

 def test_not_enabled_without_explicit_director_instruction(self):
  with patch.dict('os.environ',{'MATRIX_PRODUCTION_GENERATE_ONCE':''}),patch.object(g.threading,'Thread') as t:
   g.kickoff()
   t.assert_not_called()
 def test_exact_enabled_flag_only(self):
  with patch.dict('os.environ',{'MATRIX_PRODUCTION_GENERATE_ONCE':g.RUN_TAG}),patch.object(g.threading,'Thread') as t:
   g.kickoff()
   t.assert_called_once()
 def test_no_duplicate_paid_generations(self):
  with patch('startup_generation.activate_actor',return_value='director'),patch('startup_generation.clear_actor'),patch(
   'durable_campaign_store.is_configured',return_value=True),patch(
   'durable_campaign_store.list_batches',return_value=[{'id':'prior','brief':'hello '+g.RUN_TAG}]),patch(
   'director_ai_studio.create_ai_batch') as create:
   g.run()
   create.assert_not_called()
