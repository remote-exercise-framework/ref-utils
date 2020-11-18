#!/usr/bin/env python3
"""Setup"""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read() # pylint: disable = invalid-name

setuptools.setup(
    name="ref_utils",
    version="0.1.8",
    author="Nils Bars, Moritz Schloegel",
    author_email="nils.bars@rub.de, moritz.schloegel@rub.de",
    description="A package containing various utility functions for remote-exercise-framework submission process",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    package_data={"ref_utils": ["py.typed"]},
    packages=["ref_utils"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
    install_requires=["colorama==0.4.3"],

)
