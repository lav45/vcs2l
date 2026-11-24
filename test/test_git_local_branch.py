"""Tests for local branches without a remote counterpart: pull and re-import."""

import os
import subprocess
import sys
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


def _branch(cwd):
    return subprocess.check_output(
        ['git', 'symbolic-ref', '--short', 'HEAD'], cwd=cwd, env=GIT_ENV, text=True
    ).strip()


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


class TestGitImportLocalBranch(unittest.TestCase):
    def setUp(self):
        self._temp = TemporaryDirectory()
        self.root = self._temp.name
        self.origin = os.path.join(self.root, 'origin')
        os.mkdir(self.origin)
        _git('init', '-q', '-b', 'main', cwd=self.origin)
        _git('commit', '-q', '--allow-empty', '-m', 'init', cwd=self.origin)
        self.workspace = os.path.join(self.root, 'workspace')
        self.clone = os.path.join(self.workspace, 'clone')
        _git('clone', '-q', self.origin, self.clone, cwd=self.root)
        _git('switch', '-q', '-c', 'local-only', cwd=self.clone)
        _git('commit', '-q', '--allow-empty', '-m', 'local', cwd=self.clone)
        _git('switch', '-q', 'main', cwd=self.clone)

    def tearDown(self):
        self._temp.cleanup()

    def _import(self, version):
        repos = os.path.join(self.root, 'local.repos')
        with open(repos, 'w') as f:
            f.write(
                'repositories:\n'
                '  clone:\n'
                '    type: git\n'
                '    url: %s\n'
                '    version: %s\n' % (self.origin, version)
            )
        repo_root = os.path.dirname(os.path.dirname(__file__))
        return subprocess.run(
            [
                sys.executable,
                os.path.join(repo_root, 'scripts', 'vcs-import'),
                '--input',
                repos,
                self.workspace,
            ],
            capture_output=True,
            text=True,
            env={
                **GIT_ENV,
                'PYTHONPATH': repo_root + os.pathsep + os.environ.get('PYTHONPATH', ''),
            },
        )

    def test_local_branch_is_checked_out(self):
        result = self._import('local-only')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(_branch(self.clone), 'local-only')

    def test_missing_version_is_a_failure(self):
        result = self._import('missing')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(_branch(self.clone), 'main')


if __name__ == '__main__':
    unittest.main()
