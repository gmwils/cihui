# -*- coding: utf-8 -*-
# Copyright (c) 2012 Geoff Wilson <gmwils@gmail.com>

import base64
import functools
import json
import tornado.web

from cihui import atom_formatter
from cihui import formatter

from tornado import gen


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, list_db):
        self.list_db = list_db

    def get_current_user(self):
        # TODO(gmwils): refactor & test
        session_key = self.get_secure_cookie('session_id')
        if session_key:
            return str(session_key, encoding='ascii').split('|')[1]

        return None


def make_stub(list_id, stub=''):
    if stub:
        return '%s-%s' % (list_id, stub)

    return list_id


class UserHandler(BaseHandler):
    def initialize(self, account_db):
        self.account_db = account_db

    def get(self, username):
        if username == 'new':
            self.render('user/new.html')
        else:
            # TODO(gmwils): get user info from the database
            self.render('user/show.html', username=username)


# TODO(gmwils): LogoutHandler
class LoginHandler(tornado.web.RequestHandler):
    def initialize(self, account_db):
        self.account_db = account_db

    def get(self):
        self.render('login.html')

    @tornado.web.asynchronous
    def post(self):
        # TODO(gmwils): document API
        # TODO(gmwils): test from the view layer using selenium
        # TODO(gmwils): handle account creation
        # TODO(gmwils): use sensible salted passwords
        # TODO(gmwils): authorize against the account_db
        # TODO(gmwils): require HTTPS for login/app
        username = self.get_argument('user')
        password = self.get_argument('passwd')
        next_url = self.get_argument('next', '/')
        self.account_db.authenticate_web_user(username, password, next_url, self.authenticated)

    @tornado.web.asynchronous
    def authenticated(self, session_id=None, redirect_url=None, username=None):
        # TODO(gmwils): include a proper session id that can expire
        if session_id is not None:
            self.set_secure_cookie('session_id', '%s|%s' % (session_id, username))
            self.redirect(redirect_url)
        else:
            # TODO(gmwils): show a login failure message
            self.redirect('/')


class MainHandler(BaseHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        word_lists = yield gen.Task(self.list_db.get_lists)
        if word_lists is None:
            word_lists = []

        def add_stub(word_list):
            word_list['stub'] = make_stub(word_list.get('id'), word_list.get('stub'))
            return word_list

        word_lists = list(map(add_stub, word_lists))

        self.render('index.html', word_lists=word_lists)


class AtomHandler(BaseHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        word_lists = yield gen.Task(self.list_db.get_lists)
        entry_list = []
        for word_list in word_lists:
            entry = {'title': word_list.get('title'),
                     'link': '/list/%s' % make_stub(word_list.get('id'), word_list.get('stub'))}
            entry_list.append(entry)

        self.write(atom_formatter.format_atom(title='CiHui', entries=entry_list))
        self.finish()


class WordListHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self, list_id, list_format):
        callback = self.render_html_list

        if list_format == '.csv':
            callback = self.received_csv_list
        elif list_format == '.tsv':
            callback = self.received_tsv_list

        self.list_db.get_word_list(int(list_id), callback)

    @tornado.web.asynchronous
    def received_csv_list(self, word_list):
        """ Return list in CSV format """
        self.set_header('Content-Type', 'text/csv; charset=utf-8')
        self.set_status(200)
        for word in word_list['words']:
            self.write('%s\n' % (formatter.format_word_as_csv(word)))

        self.finish()

    @tornado.web.asynchronous
    def received_tsv_list(self, word_list):
        """ Return list in Tab separated format """
        self.set_header('Content-Type', 'text/tsv; charset=utf-8')
        self.set_status(200)
        for word in word_list['words']:
            self.write('%s\n' % (formatter.format_word_as_tsv(word)))

        self.finish()

    @tornado.web.asynchronous
    def render_html_list(self, word_list):
        """ Render list as HTML page """
        def add_description(entry):
            if entry is not None:
                entry.append(formatter.format_description(entry[2]))
            return entry

        if word_list is not None:
            if word_list.get('words') is None:
                word_list['words'] = []
            word_list['words'] = list(map(add_description, word_list['words']))
            word_count = len(word_list['words'])
            self.render('word_list.html', word_list=word_list, word_count=word_count)
        else:
            self.send_error(404)


