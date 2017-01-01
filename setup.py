# -*- coding: utf-8 -*-
"""Installer for the pycloud package."""

from setuptools import find_packages
from setuptools import setup


long_description = '\n\n'.join([
    open('README.rst').read(),
    open('CONTRIBUTORS.rst').read(),
    open('CHANGES.rst').read(),
])


setup(
    name='pycloud',
    version='1.0a1',
    description="A client library for pCloud",
    long_description='',  #long_description,
    # Get more from https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Environment :: Web Environment",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    keywords='Python pCloud REST',
    author='Tom Gross',
    author_email='itconsense@gmail.com',
    url='https://pypi.python.org/pypi/pycloud',
    license='MIT',
    packages=find_packages('src', exclude=['ez_setup']),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests',
        'setuptools',
    ],
    entry_points={
        'console_scripts': [
            'pycloud-cli = pycloud.api:main',
        ]
    }
)
