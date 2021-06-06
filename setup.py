"Setup script for pysimplesql"

from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def main():
    "Executes setup when this script is the top-level"
    import pysimplesql as app

    setup(
        name=app.__name__,
        version=app.__version__,
        author=app.__author__,
        author_email=app.__author_email__,
        description=app.__doc__,
        long_description=read('README.md'),
        long_description_content_type="text/markdown",
        keywords=app.__keywords__,
        url=app.__url__,
        download_url=f"https://github.com/PySimpleSQL/pysimplesql/archive/refs/tags/v{app.__version__}.tar.gz",
        packages=find_packages(),
        install_requires=app.__requires__,
        extras_require=app.__extra_requires__,
        classifiers=app.__classifiers__,
        license=[
            c.rsplit('::', 1)[1].strip()
            for c in app.__classifiers__
            if c.startswith('License ::')
        ][0],
        include_package_data=True,
        platforms=app.__platforms__,
    )

if __name__ == '__main__':
    main()

