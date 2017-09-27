from setuptools import setup, find_packages

setup(
    name='graphql-to-rest',
    version='1.0',
    description='Make any REST API compatible with GraphQL',
    url='https://github.com/curiousest/graphql-to-rest',
    author='Douglas Hindson',
    author_email='dmhindson+pypi@gmail.com',
    packages=find_packages(),
    install_requires=[
        'requests',
        'graphene',
        'pytest',
    ],
    dependency_links=[
        'http://github.com/curiousest/promise/tarball/master#egg=promise'
    ]
)
