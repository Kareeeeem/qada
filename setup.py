from setuptools import setup

setup(
    name='qada',
    version='0.1',
    py_modules=['qada'],
    install_requires=[
        'Click',
    ],
    entry_points='''
    [console_scripts]
    qada=qada:cli
    ''',
)
