from openprocurement.api.tests.base import snitch
from openprocurement.relocation.core.tests.transfer_blanks import change_ownership, change_ownership_invalid


class OwnershipChangeTestMixin(object):
    initial_data = {}
    first_owner = 'broker'
    second_owner = 'broker1'
    test_owner = 'broker1t'
    invalid_owner = 'broker3'
    initial_auth = ('Basic', (first_owner, ''))
    resource = ""
    transfer = ""
    first_owner_token = ""
    test_transfer_data = {}
    owner_check = False

    test_change_ownership = snitch(change_ownership)
    test_change_ownership_invalid = snitch(change_ownership_invalid)
