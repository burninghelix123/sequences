#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import re
from os.path import dirname
from os.path import join

from setuptools import setup
from setuptools import find_packages

import versioneer

requirements = [
    'pyyaml>=3.11',
    'scandir',
    'P4Python',
    # eg: 'aspectlib==1.1.1', 'six>=1.7',
]


test_requirements = [
    # TODO: put package test requirements here
]


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


setup(
    name='sequences',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Matches and provied various functionality for strings and paths with sequence numbers',
    license="MIT",
    author='Craig Barnett',
    author_email='cbarnett@talesfrompipeline.com',
    url='https://github.com/burninghelix123/sequences',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={},
    include_package_data=True,
    # Requirements
    install_requires=requirements,
    tests_require=test_requirements,
    zip_safe=False,
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    test_suite='tests',
)
