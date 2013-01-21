#!/usr/bin/env python

import sys
import subprocess
import pystmark
import shlex
from setuptools import setup, find_packages

install_requires = ['requests>=1.1.0']

def test():
    pep8 = 'pep8 pystmark tests'
    pyflakes = 'pyflakes pystmark tests'
    cmds = [pep8, pyflakes]
    try:
        map(subprocess.check_call, map(shlex.split, cmds))
    except subprocess.CalledProcessError:
        return 1
    return 0
        
if 'test' in sys.argv[1:]:
    sys.exit(test())

setup(name='pystmark',
      version=pystmark.__version__,
      description='A Python library for OAuth 1.0/a, 2.0, and Ofly.',
      long_description=open('README.md').read(),
      author='Steve Leonard',
      author_email='sleonard76@gmail.com',
      url='https://github.com/xsleonard/pystmark',
      packages=find_packages(),
      install_requires=install_requires,
      license='MIT',
      classifiers=(
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        )
    )
