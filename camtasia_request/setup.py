import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid==1.5.7',
    'pyramid_debugtoolbar==2.3',
    'waitress==0.8.9',
    'wtforms==2.0.2',
    'requests==2.7.0',
    'WebTest==2.0.18',
    'pyramid-jinja2==2.5',
    'pyramid-mailer==0.14.1',
    'BTrees==4.1.2',
    'CourseCombine==0.0',
    'Jinja2==2.7.3',
    'Mako==1.0.1',
    'MarkupSafe==0.23',
    'PasteDeploy==1.5.2',
    'Pygments==2.0.2',
    'WTForms==2.0.2',
    'WebOb==1.4.1',
    'ZConfig==3.0.4',
    'ZEO==4.1.0',
    'ZODB==4.1.0',
    'ZODB3==3.11.0',
    'argparse==1.2.1',
    'beautifulsoup4==4.3.2',
    'gevent==1.0.2',
    'greenlet==0.4.7',
    'gunicorn==19.3.0',
    'iso8601==0.1.10',
    'mock==1.0.1',
    'nose==1.3.7',
    'peppercorn==0.5',
    'persistent==4.0.9',
    'pyramid-mako==1.0.2',
    'pyramid-tm==0.11',
    'pyramid-zodbconn==0.7',
    'repoze.lru==0.6',
    'repoze.sendmail==4.2',
    'six==1.9.0',
    'transaction==1.4.3',
    'translationstring==1.3',
    'venusian==1.0',
    'wsgiref==0.1.2',
    'zc.lockfile==1.1.0',
    'zdaemon==4.1.0',
    'zodburi==2.0',
    'zope.deprecation==4.1.2',
    'zope.interface==4.1.2',
    ]

setup(name='camtasia_request',
      version='0.0',
      description='camtasia_request',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Brian Looker',
      author_email='lookerb@uwosh.edu',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="camtasia_request",
      entry_points="""\
      [paste.app_factory]
      main = camtasia_request:main
      """,
      )
