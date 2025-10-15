# -*- coding: utf-8 -*-

from setuptools import setup, find_namespace_packages

with open('README.rst', encoding='utf-8') as f:
    readme = f.read()

# with open('LICENSE', encoding='utf-8') as f:
#     license_text = f.read()

setup(
    name='stackql-deploy',
    version='1.8.8',
    description='Model driven resource provisioning and deployment framework using StackQL.',
    long_description=readme,
    long_description_content_type='text/x-rst',
    author='Jeffrey Aven',
    author_email='javen@stackql.io',
    url='https://github.com/stackql/stackql-deploy',
    license='MIT',
    packages=find_namespace_packages(include=['stackql_deploy*']),
    package_data={
        'stackql_deploy': [
            'templates/**/*.template',  # Include template files recursively
            'inc/contributors.csv'      # Fixed path for contributors
        ],
    },

    # Install shell completion scripts to system share directory
    data_files=[
        ('share/stackql-deploy/completions', [
            'shell_completions/stackql-deploy-completion.bash',
            'shell_completions/stackql-deploy-completion.zsh',
            'shell_completions/stackql-deploy-completion.fish',
            'shell_completions/stackql-deploy-completion.ps1',
        ])
    ],

    include_package_data=True,
    install_requires=[
        'click',
        'python-dotenv',
        'jinja2',
        'pystackql>=3.8.1',
        'PyYAML'
    ],
    entry_points={
        'console_scripts': [
            'stackql-deploy = stackql_deploy.cli:cli',
        ],
    },
    classifiers=[
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ]
)
