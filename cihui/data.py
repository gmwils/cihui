# -*- coding: utf-8 -*-
# Copyright (c) 2012 Geoff Wilson <gmwils@gmail.com>

from cihui import database_url
from cihui import uri

import datetime
import functools
import json
import logging
import momoko
import os


class BaseDatabase(object):
    def __init__(self):
        self.callback_counter = 0
        # TODO(gmwils): Ensure the dict doesn't grow forever. Compact somehow
        self.callbacks = {}

    def add_callback(self, cb, rock=''):
        cb_counter = self.callback_counter
        self.callback_counter += 1
        cb_id = '%d|%s' % (cb_counter, rock)

        self.callbacks[cb_id] = cb

        return cb_id

    def get_callback(self, cb_id):
        callback = self.callbacks.get(cb_id, None)
        _, rock = cb_id.split('|', 2)

        if callback is not None:
            del self.callbacks[cb_id]

        return callback, rock


class AsyncDatabase(BaseDatabase):
    def __init__(self, db_url, db=None):
        super(AsyncDatabase, self).__init__()

        if db is not None:
            self.db = db
        else:
            settings = database_url.build_settings_from_dburl(db_url)
            if settings.get('user') is not None:
                dsn = 'dbname=%s user=%s password=%s host=%s port=%s' % (
                    settings.get('database'),
                    settings.get('user', ''),
                    settings.get('password', ''),
                    settings.get('host', 'localhost'),
                    settings.get('port', 5432))
            else:
                dsn = 'dbname=%s host=%s port=%s' % (
                    settings.get('database'),
                    settings.get('host', 'localhost'),
                    settings.get('port', 5432))

            self.db = momoko.Pool(dsn)


class AccountData(AsyncDatabase):
    def __init__(self, db_url, db=None):
        super(AccountData, self).__init__(db_url, db)

    def authenticate_api_user(self, user, passwd):
        valid_user = os.environ.get('API_USER', 'user')
        valid_passwd = os.environ.get('API_PASS', 'secret')

        return (user == valid_user and passwd == valid_passwd)

    def get_account(self, email, callback):
        cb_id = self.add_callback(callback, email)
        cb = functools.partial(self._on_get_account_response, cb_id)

        self.db.execute('SELECT * FROM account WHERE email = %s;', (email,),
                        callback=cb)

    def _on_get_account_response(self, cb_id, cursor, error=None):
        callback, email = self.get_callback(cb_id)

        if len(cursor) == 0:
            callback(None)
        else:
            # TODO(gmwils) build an account object
            callback(cursor.fetchall())


class ListData(AsyncDatabase):
    def __init__(self, db_url, db=None):
        super(ListData, self).__init__(db_url, db)

    def get_lists(self, callback):
        cb_id = self.add_callback(callback)
        cb = functools.partial(self._on_get_lists_response, cb_id)

        self.db.execute('SELECT id, title, stub FROM list ORDER BY modified_at DESC;',
                        callback=cb)

    def _on_get_lists_response(self, cb_id, cursor, error=None):
        callback, _ = self.get_callback(cb_id)

        if cursor is None or cursor.rowcount == 0:
            logging.warning('No lists found in database')
            callback(None)
        else:
            word_lists = []
            for word_list in cursor:
                word_lists.append({'id': word_list[0], 'title': word_list[1],
                                   'stub': word_list[2]})

            callback(word_lists)

    def get_word_list(self, list_id, callback):
        cb_id = self.add_callback(callback, list_id)
        cb = functools.partial(self._on_get_word_list_response, cb_id)

        self.db.execute('SELECT id, title, words FROM list WHERE id = %s;',
                        (list_id,),
                        callback=cb)

    def _on_get_word_list_response(self, cb_id, cursor, error=None):
        callback, list_id = self.get_callback(cb_id)

        if cursor.rowcount != 1:
            logging.warning('Invalid response for get_word_list(%s)', list_id)
            callback(None)
            return

        result = cursor.fetchone()
        word_list = {}
        if len(result) > 2:
            word_list['id'] = result[0]
            word_list['title'] = result[1]
            words = result[2]
            if words is not None:
                words = json.loads(words)

            word_list['words'] = words

        callback(word_list)

    def list_exists(self, list_name, callback):
        cb_id = self.add_callback(callback, list_name)
        cb = functools.partial(self._on_list_exists, cb_id)
        self.db.execute('SELECT max(id) FROM list WHERE title=%s', (list_name,),
                        callback=cb)

    def _on_list_exists(self, cb_id, cursor, error=None):
        exists = False
        callback, list_name = self.get_callback(cb_id)

        result = cursor.fetchone()
        if result is not None:
            list_id = result[0]
            callback(list_id)
        else:
            callback(None)

    def create_list(self, list_name, list_elements, callback, list_id=None):
        cb_id = self.add_callback(callback, list_id)
        cb = functools.partial(self._on_create_list_response, cb_id)

        if list_id is not None:
            self.db.execute(
                'UPDATE list SET words=%s, modified_at=%s, stub=%s WHERE id=%s',
                (json.dumps(list_elements),
                 datetime.datetime.now(),
                 uri.title_to_stub(list_name),
                 list_id),
                 callback=cb)

        else:
            self.db.execute(
                'INSERT INTO list (title, words, stub) VALUES (%s, %s, %s) RETURNING id',
                (list_name,
                 json.dumps(list_elements),
                 uri.title_to_stub(list_name)),
                 callback=cb)

    def _on_create_list_response(self, cb_id, cursor, error=None):
        callback, list_id_str = self.get_callback(cb_id)

        if callback is None:
            # XXX(gmwils) should log an error here
            return

        if error is not None:
            callback(False)
            return

        list_id = None
        try:
            list_id = int(list_id_str)
        except ValueError:
            pass

        if list_id is None:
            result = cursor.fetchone()
            list_id = result[0]

        callback(True, list_id=list_id)
