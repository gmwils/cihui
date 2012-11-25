# -*- coding: utf-8 -*-
# Copyright (c) 2012 Geoff Wilson <gmwils@gmail.com>

import base64
import json
import tornado.web


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, database):
        self.db = database


class MainHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self):
        self.db.get_lists(self.received_lists)

    def received_lists(self, word_lists):
        msg = u"你好，世界!"

        self.render('index.html', message=msg, word_lists=word_lists)


class WordListHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self, list_id):
        self.db.get_word_list(int(list_id), self.received_list)

    @tornado.web.asynchronous
    def received_list(self, word_list):
        if word_list is not None:
            if word_list.get('words') is None:
                word_list['words'] = []
            self.render('word_list.html', word_list=word_list)
        else:
            self.send_error(404)


class APIHandler(BaseHandler):
    def check_xsrf_cookie(self):
        """ Disable cross site cookies on the API methods """
        pass

    def _execute(self, transforms, *args, **kwargs):
        """ Wrap the _execute method with basic authentication """
        if not self.require_basic_auth(kwargs):
            return False
        return super(APIHandler, self)._execute(transforms, *args, **kwargs)

    def set_unauthorized_headers(self):
        self.set_status(401)
        self.set_header('WWW-Authenticate', 'Basic realm=Restricted')
        self._transforms = []
        self.finish()

    def require_basic_auth(self, kwargs):
        """ Enforce basic authentication """
        auth_header = self.request.headers.get('Authorization')
        if auth_header is None or not auth_header.startswith('Basic '):
            self.set_unauthorized_headers()
            return False

        auth_decoded = base64.decodestring(auth_header[6:])
        user, passwd = auth_decoded.split(':', 2)
        if self.authenticate_api_user(user, passwd):
            return True

        self.set_unauthorized_headers()
        return False

    def authenticate_api_user(self, user, passwd):
        return self.db.authenticate_api_user(user, passwd)


class APIAccountHandler(APIHandler):
    @tornado.web.asynchronous
    def get(self):
        email = self.get_argument('email', None)

        if email is not None:
            self.db.get_account(email, self.got_account)
        else:
            self.got_account(None)

    @tornado.web.asynchronous
    def post(self):
        email = self.get_argument('email', 'No data received')

        self.db.get_account(email, self.got_account)

    def got_account(self, account):
        if account is not None:
            self.write('Received email: "%s", id: %s' % (account['email'], account['id']))
        else:
            # TODO(gmwils): set an error code
            self.write('No account received')

        self.finish()


class APIListHandler(APIHandler):
    @tornado.web.asynchronous
    def post(self):
        body = json.loads(self.request.body)
        list_name = body.get('title', None)
        words = body.get('words', None)

        if list_name is None:
            self.created_list(False, 'Missing title')
            return

        if words is None or len(words) == 0:
            self.created_list(False, 'No word list supplied')
            return

        self.db.create_list(list_name, words, self.created_list)

    def created_list(self, success, reason=None):
        if success:
            self.set_status(201)
            self.write('')
        else:
            self.set_status(500)
            if reason is not None:
                self.write('Error: %s' % reason)
            else:
                self.write('Failed to create list.')

        self.finish()
