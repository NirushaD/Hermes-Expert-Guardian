from pathlib import Path
import shutil
import subprocess
import unittest


class FrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for frontend interaction tests')
    def test_review_approval_flow(self):
        result = subprocess.run([shutil.which('node'), str(Path(__file__).with_name('frontend_reviews.mjs'))],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
