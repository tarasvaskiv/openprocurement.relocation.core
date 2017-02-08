# -*- coding: utf-8 -*-
import os
import unittest
import webtest
from datetime import datetime
from uuid import uuid4

from openprocurement.api.design import sync_design
from openprocurement.api.tests.base import PrefixedRequestClass

test_transfer_data = {}
now = datetime.now()


class BaseWebTest(unittest.TestCase):
    """Base Web Test to test openprocurement.relocation.api.

    It setups the database before each test and delete it after.
    """
    initial_auth = ('Basic', ('broker', ''))
    relative_to = os.path.dirname(__file__)

    @classmethod
    def setUpClass(cls):
        cls.app = webtest.TestApp("config:tests.ini", relative_to=cls.relative_to)
        cls.app.RequestClass = PrefixedRequestClass
        cls.couchdb_server = cls.app.app.registry.couchdb_server
        cls.db = cls.app.app.registry.db
        cls.db_name = cls.db.name

    @classmethod
    def tearDownClass(cls):
        try:
            cls.couchdb_server.delete(cls.db_name)
        except:
            pass

    def setUp(self):
        self.db_name += uuid4().hex
        self.couchdb_server.create(self.db_name)
        db = self.couchdb_server[self.db_name]
        sync_design(db)
        self.app.app.registry.db = db
        self.db = self.app.app.registry.db
        self.db_name = self.db.name
        self.app.authorization = self.initial_auth

    def tearDown(self):
        self.couchdb_server.delete(self.db_name)
