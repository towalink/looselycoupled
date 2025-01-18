import os
import setuptools


with open('README.md', 'r') as f:
    long_description = f.read()

setup_kwargs = {
    'name': 'asyncmodule',
    'version': '0.1.0',
    'author': 'Dirk Henrici',
    'author_email': 'towalink.asyncmodules@henrici.name',
    'description': 'simplistic asyncio-based framework for loosely coupling application modules that can interact synchronously and asynchronously (event queue)',
    'long_description': long_description,
    'long_description_content_type': 'text/markdown',
    'url': 'https://www.github.com/towalink/asyncmodules',
    'packages': setuptools.find_namespace_packages('src'),
    'package_dir': {'': 'src'},
    'include_package_data': True,
    'install_requires': ['cherrypy',
                         'jinja2',
                         'pyyaml'
                        ],
    'entry_points': '''
        [console_scripts]
        asyncmodules=asyncmodules:main
    ''',
    'classifiers': [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology'
    ],
    'python_requires': '>=3.8',
    'keywords': 'event-driven asynchronous asyncio messaging',
    'project_urls': {
        'Project homepage': 'https://www.github.com/towalink/asyncmodules',
        'Repository': 'https://www.github.com/towalink/asyncmodules',
        'PyPi': 'https://pypi.org/project/asyncmodules/'
    },
}


if __name__ == '__main__':
    setuptools.setup(**setup_kwargs)
