"""Tests for GitClient.pull on branches without a remote counterpart."""

import os
import subprocess
import unittest
from tempfile import TemporaryDirectory

from vcs2l.clients.git import GitClient

GIT_ENV = {
    **os.environ,
    'GIT_AUTHOR_NAME': 'vcs2l',
    'GIT_AUTHOR_EMAIL': 'vcs2l@example.com',
    'GIT_COMMITTER_NAME': 'vcs2l',
    'GIT_COMMITTER_EMAIL': 'vcs2l@example.com',
}


def _git(*args, cwd):
    subprocess.check_call(
        ['git', *args],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=GIT_ENV,
    )


def _head(cwd):
    return subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=cwd, env=GIT_ENV, text=True
    ).strip()


class TestGitPull(unittest.TestCase):
    def setUp(self):
        self._temp = TemporaryDirectory()
        self.root = self._temp.name
        self.origin = os.path.join(self.root, 'origin')
        os.mkdir(self.origin)
        _git('init', '-q', '-b', 'main', cwd=self.origin)
        _git('commit', '-q', '--allow-empty', '-m', 'init', cwd=self.origin)
        self.clone = os.path.join(self.root, 'clone')
        _git('clone', '-q', self.origin, self.clone, cwd=self.root)

    def tearDown(self):
        self._temp.cleanup()

    def test_tracking_branch_is_pulled(self):
        _git('commit', '-q', '--allow-empty', '-m', 'next', cwd=self.origin)
        result = GitClient(self.clone).pull(None)
        self.assertEqual(result['returncode'], 0, result['output'])
        self.assertEqual(_head(self.clone), _head(self.origin))

    def test_branch_without_upstream_is_not_a_failure(self):
        _git('switch', '-q', '-c', 'local-only', cwd=self.clone)
        result = GitClient(self.clone).pull(None)
        self.assertEqual(result['returncode'], 0, result['output'])
        self.assertTrue(result['output'])

    def test_unreachable_upstream_is_a_failure(self):
        _git(
            'remote',
            'set-url',
            'origin',
            os.path.join(self.root, 'missing'),
            cwd=self.clone,
        )
        result = GitClient(self.clone).pull(None)
        self.assertNotEqual(result['returncode'], 0, result['output'])


if __name__ == '__main__':
    unittest.main()
