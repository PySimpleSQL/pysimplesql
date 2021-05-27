#!/usr/bin/python3
from setuptools import setup, find_packages

def readme():
    try:
        with open('README.md') as f:
            return f.read()
    except IOError:
        return ''

requirements = ['PySimpleGUI','update_checker']

setup(
    name="pysimplesql",
    version="0.0.9",
    author="Jonathan Decker",
    author_email="pysimplesql@gmail.com",
    description="sqlite3 database binding for PySimpleGUI",
    long_description=readme(),
    long_description_content_type="text/markdown",
    keywords="SQL sqlite database application front-end access libre office GUI PySimpleGUI",
    url="https://github.com/PySimpleSQL/pysimplesql",
    download_url="https://github.com/PySimpleSQL/pysimplesql/archive/refs/tags/0.0.9.tar.gz",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent",
    ],
)
