# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.tests.base import snitch
from openprocurement.relocation.core.tests.base import BaseWebTest
from openprocurement.relocation.core.tests.transfer_blanks import (
    simple_add_transfer, get_transfer, not_found, create_transfer
)


class TransferTest(BaseWebTest):

    test_simple_add_transfer = snitch(simple_add_transfer)


class TransferResourceTest(BaseWebTest):
    """ /transfers resource test """

    test_get_transfer = snitch(get_transfer)
    test_not_found = snitch(not_found)
    test_create_transfer = snitch(create_transfer)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TransferTest))
    suite.addTest(unittest.makeSuite(TransferResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
