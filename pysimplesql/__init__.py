"Sqlite3 binding for PySimpleGUI"

from .pysimplesql import *
from update_checker import UpdateChecker

__name__ = "pysimplesql"
__version__ = "develop"
__keywords__ = ["SQL", "sqlite", "sqlite3", "database", "front-end", "access", "libre office", "GUI", "PySimpleGUI"]
__author__ = "Jonathan Decker"
__author_email__ = "pysimplesql@gmail.com"
__url__ = "https://github.com/PySimpleSQL/pysimplesql"
__platforms__ = "ALL"
__classifiers__ = [
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent",
]
__requires__ =  ['PySimpleGUI','update_checker']
__extra_requires__ = {
}

# -------------------------
# Check for package updates
# -------------------------
checker = UpdateChecker()
result = checker.check('pysimplesql', __version__)
if result is not None:
    release_date=f'(released {result.release_date}) ' if result.release_date is not None else ''
    print(f'***** pysimplesql update from {__version__} to {result.available_version} {release_date} available! Be sure to run pip3 install pysimplesql --upgrade *****')
