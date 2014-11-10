"""
Flask-SimpleRest
----------------
Simple barebones to developing an Flask REST API.

Links
`````
* `development version
  <https://github.com/felipeblassioli/flask_rest>`_


"""
from setuptools import setup


setup(
    name='Flask-SimpleRest',
    version='0.3.1',
    url='https://github.com/felipeblassioli/flask_rest',
    author='Felipe Blassioli',
    author_email='felipeblassioli@gmail.com',
    description='Misc for developing a REST API',
    long_description=__doc__,
    packages=['flask_simplerest'],
    namespace_packages=['flask_simplerest'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask>=0.7',
        'flask-classy>=0.6.8',
    ]
)
