"""Setup script for pysimplesql."""

import os

from setuptools import find_packages, setup


def read(fname):
    """Utility function to read the README file.

    Used for the long_description. It's nice, because now 1) we have a top level
    README file and 2) it's easier to type in the README file than to put a raw
    string in below
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()  # noqa: SIM115


def main() -> None:
    """Executes setup when this script is the top-level."""
    import pysimplesql as app

    setup(
        name=app.__name__,
        version=app.__version__,
        author=app.__author__,
        author_email=app.__author_email__,
        description=app.__doc__,
        long_description=read("README.md"),
        long_description_content_type="text/markdown",
        keywords=app.__keywords__,
        url=app.__url__,
        download_url=f"https://github.com/PySimpleSQL/pysimplesql/archive/refs/tags/v{app.__version__}.tar.gz",
        packages=find_packages(),
        install_requires=app.__requires__,
        extras_require=app.__extra_requires__,
        classifiers=app.__classifiers__,
        license=next(
            c.rsplit("::", 1)[1].strip()
            for c in app.__classifiers__
            if c.startswith("License ::")
        ),
        include_package_data=True,
        platforms=app.__platforms__,
    )


if __name__ == "__main__":
    main()
