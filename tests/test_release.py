"""Privacy and runtime package regression tests."""
import unittest
import package
from guardian import privacy


class ReleaseTests(unittest.TestCase):
    def test_patterns_preserve_detection(self):
        values = ['PASSWORD=example', 'passwd example', 'passphrase example', 'secret example',
                  'token example', 'bearer example', 'cookie example', 'api_key example',
                  'api-key example', 'apikey example', 'credential example', 'private-key',
                  '.ssh', '.env', 'auth.json', 'BEGIN EXAMPLE KEY', 'ignore these instructions',
                  'system prompt', 'https://example.invalid/user@host']
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(privacy.redact(value), '[WITHHELD]')
                with self.assertRaises(ValueError): privacy.safe_text(value)
        self.assertEqual(privacy.safe_text('Package installation fails'), 'Package installation fails')

    def test_release_is_complete_and_byte_identical(self):
        for relative in package.FILES:
            with self.subTest(relative=relative):
                self.assertEqual((package.ROOT / relative).read_bytes(), (package.RELEASE / relative).read_bytes())
        self.assertEqual((package.RELEASE / 'README.md').read_bytes(), (package.ROOT / 'docs/INSTALL.md').read_bytes())

    def test_release_has_only_runtime_allowlist(self):
        actual = {p.relative_to(package.RELEASE).as_posix() for p in package.RELEASE.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(actual, set(package.FILES) | {'README.md'})
        self.assertTrue((package.ROOT / 'tests/test_guardian.py').is_file())


if __name__ == '__main__': unittest.main()
