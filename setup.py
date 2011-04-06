from setuptools import setup

version = 'master'

setup(name="channelguide",
      version=version,
      author='Participatory Culture Foundation',
      license='AGPL',
      packages=['channelguide'],
      install_requires=['django>=1.2, <1.3',
                        'mysql-python',
                        'python-memcached',
                        'south',
                        'feedparser'])
