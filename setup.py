# -*- coding: utf-8 -*-
"""Installer for the pcloud package."""

from setuptools import find_packages
from setuptools import setup


long_description = "\n\n".join(
    [
        open("README.rst").read(),
        open("CONTRIBUTORS.rst").read(),
        open("CHANGES.rst").read(),
    ]
)


setup(
    name="pcloud",
    version="1.4",
    description="A client library for pCloud",
    long_description=long_description,
    # Get more from https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Environment :: Web Environment",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="Python pCloud REST",
    author="Tom Gross",
    author_email="itconsense@gmail.com",
    url="https://pypi.python.org/pypi/pcloud",
    license="MIT",
    packages=find_packages("src", exclude=["ez_setup"]),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "requests",
        "requests-toolbelt",
        "wheel>=0.45.1",
        "setuptools>=75.6.0"
    ],
    extras_require={"pyfs": ["fs"]},
    entry_points={
        "fs.opener": [
            "pcloud  = pcloud.pcloudfs:PCloudOpener",
            "pcloud+eapi  = pcloud.pcloudfs:PCloudOpener",
            ],
    },
)
