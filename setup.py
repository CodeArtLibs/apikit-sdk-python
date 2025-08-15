from pathlib import Path
from setuptools import setup, find_packages

VERSION = "0.0"

tests_require = []

install_requires = []

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="apikit",
    url="https://github.com/codeartlibs/apikit-sdk-python",
    author="CodeArt",
    author_email="paulocheque@gmail.com",
    keywords="python apikit api",
    description="SDK to use with APIKit APIs",
    long_description_content_type="text/markdown",
    long_description=long_description,
    license="MIT",
    classifiers=[
        "Framework :: APIKit",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3.13",
        # 'Programming Language :: Python :: 3.14',
        # 'Programming Language :: Python :: 3.15',
        # 'Programming Language :: Python :: 3.16',
    ],
    version=VERSION,
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite="pytest",
    extras_require={"test": tests_require},
    packages=find_packages(),
)
