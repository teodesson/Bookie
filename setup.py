import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
	'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'WebTest',
    'BeautifulSoup4',
    'pyramid_mako',
	'decorator',
	'celery',
	'python-dateutil',
	'topia.termextract',
	'Unidecode',
	'py-bcrypt',
	'convoy',
	'Whoosh',
	'feedparser',
	'tweepy',
	'Whoosh',
	'breadability',
	'textblob',
	'pymysql'
]


# Add sqlite for python pre 2.5
if sys.version_info[:3] < (2, 5, 0):
    requires.append('pysqlite')


# Add sqlite for python pre 2.7
if sys.version_info[:3] < (2, 7, 0):
    requires.append('ordereddict')


setup(name='bookie',
      version='0.5.0',
      description='Bookie',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pylons",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],

      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='bookie',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = bookie:main
      """,
      paster_plugins=['pyramid'],
      )
