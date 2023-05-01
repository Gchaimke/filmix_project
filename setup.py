import os
from setuptools import setup
from filmix import app_name, version

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = app_name,
    version = version,
    author = "Chaim Gorbov",
    author_email = "gchaimke@gmail.com",
    description = ("Create films list and pars sites to get qulity status"),
    license = "BSD",
    keywords = app_name,
    url = "",
    packages=['filmix', 'tests'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 5 - Production",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)