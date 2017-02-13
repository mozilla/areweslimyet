# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from setuptools import setup

THIS_DIR = os.path.dirname(os.path.realpath(__name__))


def read(*parts):
    with open(os.path.join(THIS_DIR, *parts)) as f:
        return f.read()

setup(
    name="awsy",
    version="0.0.1",
    description="AreWeSlimYet",
    long_description="A memory testing framework for Firefox.",
    url="https://github.com/mozilla/areweslimyet",
    author="Eric Rahm",
    author_email="erahm@mozilla.com",
    license="MPL 2.0",
    classifiers=[
      "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)"
    ],
    packages=["benchtester"],
    install_requires=read('requirements.txt').splitlines(),
)
