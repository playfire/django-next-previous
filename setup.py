#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='django-next-previous',
    description="Django model mixin for easy retrieval of the 'next' and "
        "'previous' objects.",
    version='0.1',
    url='http://code.playfire.com/',

    author='Playfire.com',
    author_email='tech@playfire.com',
    license='BSD',

    packages=find_packages(),
)
