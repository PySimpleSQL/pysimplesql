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
    version="0.0.1",
    author="Jonathan Decker",
    author_email="PySimpleSQL@gmail.com",
    description="sqlite3 database binding for PySimpleGUI",
    long_description=readme(),
    long_description_content_type="text/markdown",
    keywords="SQL sqlite database application front-end access libre office GUI PySimpleGUI",
    url="https://github.com/PySimpleSQL/PySimpleSQL",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3"
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Topic :: Database :: Application",
        "Operating System :: OS Independent"
    ]
)
