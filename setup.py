from setuptools import setup, find_packages

setup(
    name='stackql-deploy',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'click',
        # other dependencies
    ],
    entry_points={
        'console_scripts': [
            'stackql-deploy = stackql_deploy.cli:cli',
        ],
    },
)
