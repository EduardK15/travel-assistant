import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DeploymentFilesTests(unittest.TestCase):
    def test_required_files_present(self):
        for name in ('requirements.txt', 'README.md', '.gitignore', '.env.example', 'Procfile', 'render.yaml'):
            with self.subTest(file=name):
                self.assertTrue((ROOT / name).is_file())

    def test_gitignore_protects_env(self):
        text = (ROOT / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('.env', text)
        self.assertIn('*.key', text)

    def test_one_worker_for_in_memory_results(self):
        self.assertIn('--workers 1', (ROOT / 'Procfile').read_text(encoding='utf-8'))
