# -*- coding: utf-8 -*-
# Copyright (c) 2012 Geoff Wilson <gmwils@gmail.com>

import base64
import functools
import json
import tornado.web

from cihui import formatter


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, list_db):
        self.list_db = list_db


class MainHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self):
        self.list_db.get_lists(self.received_lists)

    def received_lists(self, word_lists):
        def add_stub(word_list):
            if word_list.get('stub'):
                word_list['stub'] = '%s-%s' % ( word_list['id'], word_list['stub'])
            else:
                word_list['stub'] = word_list['id']

            return word_list

        word_lists = list(map(add_stub, word_lists))
        self.render('index.html', word_lists=word_lists)


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
            self.render('word_list.html', word_list=word_list)
        else:
            self.send_error(404)
