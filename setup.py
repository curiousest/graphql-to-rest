from setuptools import setup, find_packages

setup(
    name='graphql-to-rest',
    version='0.1',
    description='Make any REST API compatible with GraphQL',
    packages=find_packages(),
    install_requires=[
        'requests',
        'graphene',
        'pytest'
    ]
)
