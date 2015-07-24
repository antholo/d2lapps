'''
import unittest, os
from pyramid import testing

from paste.deploy.loadwsgi import appconfig
ini = 'config:' + os.path.join(os.path.abspath('.'), ('development.ini'))
settings = appconfig(ini, relative_to=".")



class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        print("CONFIG: ", dir(self.config))

    def tearDown(self):
        testing.tearDown()

    def test_login(self):
        from camtasia_request.views import login

        request = testing.DummyRequest()
        response = login(request)
        self.assertEqual(response.status_code, 200)

class FunctionalTests(unittest.TestCase):
    def setup(self):
        from camtasia_request import main
        app = main({})
        from webtest import TestApp
        print("IMPORT: ", TestApp)
        self.testapp = TestApp(app)
        print("TESTAPP: ", testapp)

    def test_login(self):
        res = self.testapp.get('/login', status=200)
        self.assertIn(b'<h2>Login to continue</h2>', res.body)
'''


from pyramid import testing
from webtest import TestApp
from paste.deploy import loadapp
from paste.deploy.loadwsgi import appconfig
from pyramid.config import Configurator
import unittest, os, transaction, pyramid.registry, pyramid.request

ini = 'config:' + os.path.join(os.path.abspath('.'), ('development.ini'))
settings = appconfig(ini, relative_to=".")
wsgiapp = loadapp(ini)

config = Configurator(registry=wsgiapp.registry, package='camtasia_request')
config.setup_registry(settings=settings)
app = TestApp(wsgiapp, extra_environ={})


class ViewsTests(unittest.TestCase):

    def setup(self):
        # reg = pyramid.registry.Registry('testing')
        wsgiapp = self._load_wsgiapp()
        self.config = Configurator(registry=wsgiapp.registry, package='camtasia_request')
        self.config.setup_registry(settings=settings)
        self.app = TestApp(wsgiapp, extra_environ={})

    def _load_wsgiapp(self):
        wsgiapp = loadapp(ini)
        return wsgiapp

    def _get_app_url(self):
        return 'http://localhost:5000'

    def tearDown(self):
        self.config.end()
        pass
"""
    def test_login(self):
        res = self.app.get('/login', status=200)
        self.assertTrue(res.status_code==200)
"""

'''
if __name__ == '__main__':
    unittest.main()
'''

"""
import unittest

from pyramid import testing
from pyramid.paster import get_app


class ViewTests(unittest.TestCase):
    def setUp(self):
        app = get_app('development.ini')
        self.config = testing.setUp(registry=app)
        self.config.include('pyramid_mailer.testing')

    def tearDown(self):
        testing.tearDown()
    
    def test_login(self):
        from .views import login
        request = testing.DummyRequest()
        response = login(request)
        self.assertEqual(response.status, '200 OK')
"""    

