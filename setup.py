#!/usr/bin/python3
import setuptools

def readme():
    try:
        with open('README.md') as f:
            return f.read()
    except IOError:
        return ''

requirements = ['PySimpleGUI']

setuptools.setup(
    name="PySimpleSQL",
    version="0.0.4",
    author="Jonathan Decker",
    author_email="PySimpleSQL@gmail.com",
    description="sqlite3 database binding for PySimpleGUI",
    long_description="It's alive!",#readme(),
    long_description_content_type="text/markdown",
    keywords="SQL sqlite database application front-end access libre office GUI PySimpleGUI",
    url="https://github.com/PySimpleSQL/PySimpleSQL",
    download_url="https://github.com/PySimpleSQL/PySimpleSQL/archive/refs/tags/0.0.4.tar.gz",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent",
    ],
)
