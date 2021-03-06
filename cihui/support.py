# -*- coding: utf-8 -*-
# Copyright (c) 2012 Geoff Wilson <gmwils@gmail.com>

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

import os


class HandlerTestCase(AsyncHTTPTestCase):
    """Base class for web tests that also supports WSGI mode.

    Override get_handlers and get_app_kwargs instead of get_app.
    Append to wsgi_safe to have it run in wsgi_test as well.
    """
    def get_app(self):
        self.app = Application(self.get_handlers(), **self.get_app_kwargs())
        return self.app

    def get_handlers(self):
        raise NotImplementedError()

    def get_app_kwargs(self):
        return {'cookie_secret': 'Testing all the things'}


class UITestCase(HandlerTestCase):
    def get_app_kwargs(self):
        args = super().get_app_kwargs()
        args['static_path'] = os.path.join(os.path.dirname(__file__), '../static')
        args['template_path'] = os.path.join(os.path.dirname(__file__), '../templates')
        return args
