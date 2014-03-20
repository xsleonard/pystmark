#!/usr/bin/env python

from __future__ import print_function
import subprocess
import shlex
import os
import sys
from setuptools import setup, Command
from _pystmark_meta import __version__

pypy = False
if 'pypy' in sys.version.lower():
    pypy = True


class Test(Command):
    ''' Test pystmark application with the following:
        pep8 conformance (style)
        pyflakes validation (static analysis)
        nosetests (code tests) [--with-integration] [--run-failed]
    '''
    description = 'Test Pystmark source code'
    user_options = [('run-failed', None,
                     'Run only the previously failed tests.'),
                    ('nose-only', None, 'Run only the nose tests.'),
                    ('with-integration', None,
                     'Run the integration/live tests')]
    boolean_options = ['run-failed', 'nose-only']

    def initialize_options(self):
        self.run_failed = False
        # Disable the flake8 tests in pypy due to bug in pep8 module
        self.nose_only = pypy
        self.with_integration = False
        self.flake8 = 'flake8 pystmark.py tests/'

    def finalize_options(self):
        pass

    def _no_print_statements(self):
        cmd = 'grep -rnw print pystmark.py'
        p = subprocess.Popen(shlex.split(cmd), close_fds=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        err = p.stderr.read().strip()
        if err:
            msg = 'ERROR: stderr not empty for print statement grep: {0}'
            print(msg.format(err))
            raise SystemExit(-1)
        output = p.stdout.read().strip()
        if output:
            print('ERROR: Found print statements in source code:')
            print(output)
            raise SystemExit(-1)

    def _get_py_files(self, basepath, subpath=''):
        files = []
        badchars = ['.', '_', '~']
        path = os.path.join(basepath, subpath)
        for f in os.listdir(path):
            if (not f.endswith('.py') or
                    any(map(lambda c: f.startswith(c), badchars))):
                continue
            files.append(os.path.join(subpath, f))
        return files

    def _get_nose_command(self):
        testfiles = self._get_py_files('tests/')
        if self.with_integration:
            testfiles += self._get_py_files('tests/', 'integration/')
        if not testfiles:
            print('No tests found.')
            return
        nosecmd = ('nosetests -v -w tests/ --with-coverage '
                   '--cover-package=pystmark --cover-package=_pystmark_meta '
                   '--cover-erase '
                   '--cover-min-percentage=100')
        if self.run_failed:
            nosecmd += ' --failed'
        nose = ' '.join(shlex.split(nosecmd) + testfiles)
        return nose

    def run(self):
        # TODO -- check that flake8, nosetests are installed
        cmds = [self._get_nose_command()]
        if not self.nose_only:
            self._no_print_statements()
            cmds = [self.flake8] + cmds
        cmds = filter(bool, cmds)
        if not cmds:
            print('No action taken.')
            SystemExit(-2)
        try:
            list(map(subprocess.check_call, map(shlex.split, cmds)))
        except subprocess.CalledProcessError:
            raise SystemExit(-1)
        raise SystemExit(0)


setup(name='pystmark',
      version=__version__,
      description=('A Python library for the Postmark API '
                   '(http://developer.postmarkapp.com/).'),
      long_description=open('README.md').read(),
      author='Steve Leonard',
      author_email='sleonard76@gmail.com',
      url='https://github.com/xsleonard/pystmark',
      platforms='any',
      py_modules=['pystmark', '_pystmark_meta'],
      install_requires=['requests>=1.2.0'],
      cmdclass=dict(test=Test),
      license='MIT',
      keywords='postmark postmarkapp email',
      classifiers=(
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: Implementation :: PyPy',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Communications :: Email',
      ))
