#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import os
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import relpath
from os.path import splitext

from setuptools import Extension
from setuptools import find_packages
from setuptools import setup
from setuptools.command.build_ext import build_ext

try:
    # Allow installing package without any Cython available. This
    # assumes you are going to include the .c files in your sdist.
    import Cython
except ImportError:
    Cython = None


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")
    ).read()


class CustomBuildExtCommand(build_ext):
    """build_ext command for use when numpy headers are needed."""

    def run(self):

        # Import numpy here, only when headers are needed
        import numpy

        # Add numpy headers to include_dirs
        self.include_dirs.append(numpy.get_include())

        # Call original build_ext command
        build_ext.run(self)


# Enable code coverage for C code: we can't use CFLAGS=-coverage in toxa.ini, since that may mess with compiling
# dependencies (e.g. numpy). Therefore we set SETUPPY_CFLAGS=-coverage in toxa.ini and copy it to CFLAGS here (after
# deps have been safely installed).
if "TOXENV" in os.environ and "SETUPPY_CFLAGS" in os.environ:
    os.environ["CFLAGS"] = os.environ["SETUPPY_CFLAGS"]

setup(
    name="pysight",
    version="0.11.0",
    license="Free for non-commercial use",
    description="Create images and volumes from photon lists generated by a multiscaler",
    long_description=(
        "PySight is an application aimed at generating multidimensional images"
        "from photon lists. The main use case is to parse ``.lst`` files which"
        "were generated by FAST ComTec's multiscaler, but other photon lists"
        "can also be parsed.\n\nPySight was featured in"
        "`this <https://www.osapublishing.org/optica/abstract.cfm?uri=optica-5-9-1104>`_"
        " *Optica* article, and was created in Pablo Blinder's Lab at Tel Aviv University."
    ),
    author="Hagai Har-Gil",
    author_email="hagaihargil@protonmail.com",
    url=r"https://github.com/PBLab/python-pysight/",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: Free for non-commercial use",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    keywords=["multiscaler", "photon counting", "imaging"],
    cmdclass={"build_ext": CustomBuildExtCommand},
    install_requires=[
        "numpy >= 1.17",
        "matplotlib >= 3.1",
        "pandas >= 0.25",
        "attrs == 19.3",
        "cython >= 0.29",
        "scipy >= 1.3",
        "scikit-learn >= 0.20",
        "zarr >= 2.3",
        "tqdm >= 4.29",
        "numba >= 0.43",
        "ansimarkup >= 1.4",
        "psutil >= 5.4",
        "toml >= 0.9",
    ],
    extras_require={
        "dev": [
            "pytest",
            "sphinx",
            "bumpversion",
            "twine",
            "black",
            "mypy",
            "flake8",
            "typed-ast",
        ]
    },
    setup_requires=["cython", "numpy"] if Cython else ["numpy"],
    ext_modules=[
        Extension(
            splitext(relpath(path, "src").replace(os.sep, "."))[0],
            sources=[path],
            include_dirs=[dirname(path)],
        )
        for root, _, _ in os.walk("src")
        for path in glob(join(root, "*.pyx" if Cython else "*.c"))
    ],
    data_files=[("src/pysight/configs/default.toml")],
)
