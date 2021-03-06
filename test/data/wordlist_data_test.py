# -*- coding: utf-8 -*-
# Copyright (c) 2012 Geoff Wilson <gmwils@gmail.com>

import datetime
import mock

from tornado.testing import AsyncHTTPTestCase
from cihui.data import wordlist


class WordListDataTest(AsyncHTTPTestCase):
    def get_app(self):
        self.app = mock.Mock()
        return self.app

    def setUp(self):
        AsyncHTTPTestCase.setUp(self)
        self.db = mock.Mock()
        self.callback = mock.Mock()
        self.listdata = wordlist.WordListData('', self.db)


class GetManyListsTest(WordListDataTest):
    def test_get_lists_sql(self):
        self.listdata.get_lists(self.callback)
        self.db.execute.assert_called_once()
        self.assertEqual(self.listdata.callbacks['0|'], self.callback)

    def test_got_lists(self):
        cursor = mock.MagicMock(side_effect=[])

        self.listdata.callbacks['0|'] = self.callback
        self.listdata._on_get_lists_response('0|', cursor)

        self.callback.assert_called_once_with([])


class GetWordListTest(WordListDataTest):
    def test_get_basic_list(self):
        self.listdata.get_word_list(12, self.callback)
        self.db.execute.assert_called_once()
        self.assertEqual(self.listdata.callbacks['0|12'], self.callback)

    def test_got_no_word_list(self):
        cursor = mock.MagicMock(side_effect=[])

        self.listdata.callbacks['0|'] = self.callback
        self.listdata._on_get_word_list_response('0|', cursor)

        self.callback.assert_called_once_with(None)

    def test_got_one_word_list_with_no_words(self):
        sample_date = datetime.datetime(1997, 11, 21, 16, 30)
        cursor = mock.MagicMock(side_effect=[])
        cursor.rowcount = 1
        cursor.fetchone.return_value = tuple([1, 'Test', None, sample_date, True, 1])

        self.listdata.callbacks['0|1'] = self.callback
        self.listdata._on_get_word_list_response('0|1', cursor)

        self.callback.assert_called_once_with({'id': 1,
                                               'title': 'Test',
                                               'words': None,
                                               'modified_at': sample_date,
                                               'public': True,
                                               'account_id': 1})

    def test_got_one_word_list_with_words(self):
        sample_date = datetime.datetime(1997, 11, 21, 16, 30)
        cursor = mock.MagicMock(side_effect=[])
        cursor.rowcount = 1
        cursor.fetchone.return_value = tuple([1, 'Test', '{"key": "value"}', sample_date, True, 1])

        self.listdata.callbacks['0|1'] = self.callback
        self.listdata._on_get_word_list_response('0|1', cursor)

        self.callback.assert_called_once_with({'id': 1,
                                               'title': 'Test',
                                               'words': {'key': 'value'},
                                               'modified_at': sample_date,
                                               'public': True,
                                               'account_id': 1})


class CreateListTest(WordListDataTest):
    def test_create_empty_list_sql(self):
        self.listdata.create_list('Test List', [], self.callback)
        self.db.execute.assert_called_once()
        self.assertIn('INSERT', str(self.db.execute.call_args))
        self.assertIn('test-list', str(self.db.execute.call_args))
        self.assertEqual(self.listdata.callbacks['0|None'], self.callback)

    def test_create_word_list_sql(self):
        self.listdata.create_list('Word List', [['大', 'da', ['big']], ], self.callback)
        self.db.execute.assert_called_once()
        self.assertIn('INSERT', str(self.db.execute.call_args))
        self.assertEqual(self.listdata.callbacks['0|None'], self.callback)

    def test_update_existing_list(self):
        self.listdata.create_list('Test List', [], self.callback, 1)
        self.db.execute.assert_called_once()
        self.assertIn('UPDATE', str(self.db.execute.call_args))
        self.assertIn('test-list', str(self.db.execute.call_args))
        self.assertEqual(self.listdata.callbacks['0|1'], self.callback)

    def test_created_list(self):
        cursor = mock.Mock()

        self.listdata.callbacks['0|42'] = self.callback
        self.listdata._on_create_list_response('0|42', cursor)

        self.callback.assert_called_once_with(True, list_id=42)


class ListExistsTest(WordListDataTest):
    def test_list_exists(self):
        self.listdata.list_exists('list name', self.callback)
        self.db.execute.assert_called_once()
        self.assertEqual(self.listdata.callbacks['0|list name'], self.callback)

    def test_on_list_exists(self):
        cursor = mock.MagicMock(side_effect=[])
        cursor.fetchone.return_value = tuple([1])

        self.listdata.callbacks['0|testlist'] = self.callback
        self.listdata._on_list_exists('0|testlist', cursor)

        self.callback.assert_called_once_with(True)

    def test_on_list_not_exists(self):
        cursor = mock.MagicMock(side_effect=[])
        cursor.fetchone.return_value = tuple([0])

        self.listdata.callbacks['0|testlist'] = self.callback
        self.listdata._on_list_exists('0|testlist', cursor)

        self.callback.assert_called_once_with(False)

    def test_list_exists_for_account(self):
        self.listdata.list_exists_for_account('list name', 1, self.callback)
        self.db.execute.assert_called_once()
        self.assertEqual(self.listdata.callbacks['0|list name,1'], self.callback)
