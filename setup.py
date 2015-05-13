from setuptools import find_packages, setup


setup(
    name='pydrill',
    author='Alexander Ershov',
    author_email='codumentary.com@gmail.com',
    url='https://github.com/alexandershov/pydrill',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['flask', 'Flask-SQLAlchemy', 'Flask-Script', 'flask-redis', 'PyYAML'],
)
