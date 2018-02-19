# -*- coding: utf-8 -*-
from uuid import uuid4
from copy import deepcopy

from openprocurement.relocation.core.models import Transfer


# TransferTest


def simple_add_transfer(self):
    data = {"access_token": uuid4().hex,
            "transfer_token": uuid4().hex,
            "owner": "Chuck Norris"}

    u = Transfer(data)

    assert u.id is None

    u.store(self.db)

    assert u.id is not None

    fromdb = self.db.get(u.id)

    assert u.transfer_token == fromdb['transfer_token']
    assert u.access_token == fromdb['access_token']
    assert u.owner == fromdb['owner']
    assert u.doc_type == "Transfer"

    u.delete_instance(self.db)


# TransferResourceTest


def get_transfer(self):
    response = self.app.get('/transfers', status=405)
    self.assertEqual(response.status, '405 Method Not Allowed')

    response = self.app.post_json('/transfers', {'data': self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']
    self.assertIn('id', transfer)

    response = self.app.get('/transfers/{}'.format(transfer['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data'], transfer)

    response = self.app.get('/transfers/{}?opt_jsonp=callback'.format(transfer['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/javascript')
    self.assertIn('callback({"data": {"', response.body)

    response = self.app.get('/transfers/{}?opt_pretty=1'.format(transfer['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertIn('{\n    "data": {\n        "', response.body)


def not_found(self):
    response = self.app.post_json('/transfers', {'data': self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']

    response = self.app.get('/transfers/{}'.format("1234" * 8), status=404)
    self.assertEqual(response.status, '404 Not Found')

    data = deepcopy(self.test_transfer_data)
    data['id'] = uuid4().hex
    response = self.app.post_json('/transfers', {'data': data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']
    self.assertNotEqual(transfer['id'], data['id'])

    response = self.app.get('/transfers/{}'.format(data['id']), status=404)
    self.assertEqual(response.status, '404 Not Found')

    response = self.app.get('/transfers/some_id', status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location': u'url', u'name': u'transfer_id'}
    ])

    response = self.app.patch_json(
        '/transfers/some_id', {'data': {}}, status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location': u'url', u'name': u'transfer_id'}
    ])


def create_transfer(self):
    response = self.app.post_json('/transfers', status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(response.json['errors'], [
        {u'description': u'No JSON object could be decoded', u'location': u'body', u'name': u'data'}
    ])

    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    transfer = response.json['data']
    self.assertNotIn('usedFor', transfer)
    self.assertIn('token', response.json['access'])
    self.assertIn('transfer', response.json['access'])

    response = self.app.get('/transfers/{}'.format(transfer['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(set(response.json['data']), set(transfer))
    self.assertEqual(response.json['data'], transfer)

    data = self.test_transfer_data
    response = self.app.post_json('/transfers?opt_jsonp=callback', {"data": data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/javascript')
    self.assertIn('callback({"', response.body)

    response = self.app.post_json('/transfers?opt_pretty=1', {"data": data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    self.assertIn('{\n    "', response.body)

    response = self.app.post_json('/transfers', {"data": data, "options": {"pretty": True}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    self.assertIn('{\n    "', response.body)


# OwnershipChangeTestMixin


def change_ownership_invalid(self):
    # Change auth to another owner
    authorization = self.app.authorization
    self.app.authorization = ('Basic', (self.second_owner, ''))

    # other broker can't change the object
    response = self.app.patch_json('{}?acc_token={}'.format(self.request_path, self.first_owner_token),
                                   {"data": {'description': "description 1"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    # create Transfer
    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']
    self.assertIn('date', transfer)
    transfer_creation_date = transfer['date']
    new_access_token = response.json['access']['token']
    new_transfer_token = response.json['access']['transfer']

    # try to change ownership with invalid transfer token
    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
    ])

    # change ownership
    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': self.transfer}})
    self.assertEqual(response.status, '200 OK')

    # Object location is stored in Transfer
    response = self.app.get('/transfers/{}'.format(transfer['id']))
    transfer = response.json['data']
    transfer_modification_date = transfer['date']
    self.assertEqual(transfer['usedFor'], self.request_path)
    self.assertNotEqual(transfer_creation_date, transfer_modification_date)

    # try to use already applied transfer
    self.app.authorization = authorization
    collection_path = '/'.join(self.request_path.split('/')[:-1]) + '?acc_token={}'.format(self.acc_token)
    response = self.app.post_json(collection_path, {'data': self.initial_data})
    new_item_id = response.json['data']['id']
    new_request_path = "{}/{}".format(collection_path.split('?')[0], new_item_id)
    access = response.json['access']
    self.app.authorization = ('Basic', (self.second_owner, ''))
    response = self.app.post_json('{}/ownership'.format(new_request_path),
                                  {"data": {"id": transfer['id'], 'transfer': access['transfer']}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
    ])
    # simulate half-applied transfer activation process (i.e. transfer
    # is successfully applied to a object (tender/auction) and relation is saved in transfer,
    # but object (tender/auction) is not stored with new credentials)
    transfer_doc = self.db.get(transfer['id'])
    transfer_doc['usedFor'] = new_request_path
    self.db.save(transfer_doc)
    response = self.app.post_json('{}/ownership'.format(new_request_path),
                                  {"data": {"id": transfer['id'], 'transfer': access['transfer']}}, status=200)
    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    self.app.authorization = authorization
    # old ownfer now can`t change object (tender/auction)
    response = self.app.patch_json('{}?acc_token={}'.format(self.request_path, new_access_token),
                                   {"data": {'description': "description 2"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": 'fake id', 'transfer': 'fake transfer'}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
    ])

    # try to use transfer by broker without appropriate accreditation level
    self.app.authorization = ('Basic', (self.invalid_owner, ''))

    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']

    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Broker Accreditation level does not permit ownership change',
         u'location': u'procurementMethodType', u'name': u'accreditation'}
    ])

    # test level permits to change ownership for 'test' mode
    # first try on non-test object (tender/auction)
    self.app.authorization = ('Basic', (self.test_owner, ''))
    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']
    transfer_tokens = response.json['access']

    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Broker Accreditation level does not permit ownership change',
         u'location': u'procurementMethodType', u'name': u'mode'}
    ])

    # set test mode and try to change ownership
    self.app.authorization = ('Basic', ('administrator', ''))
    resource_item = '/'.join(self.request_path.split('/')[:3])
    response = self.app.patch_json(resource_item, {'data': {'mode': 'test'}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['mode'], 'test')

    self.app.authorization = ('Basic', (self.test_owner, ''))
    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': new_transfer_token}})
    self.assertEqual(response.status, '200 OK')

    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.test_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    # test accreditation levels are also sepatated
    self.app.authorization = ('Basic', (self.invalid_owner, ''))
    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']

    new_transfer_token = transfer_tokens['transfer']
    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Broker Accreditation level does not permit ownership change',
         u'location': u'procurementMethodType', u'name': u'accreditation'}
    ])


def change_ownership(self):
    # Check owner for object !!!
    response = self.app.get('{}?acc_token={}'.format(self.request_path, self.first_owner_token))
    self.assertEqual(response.status, '200 OK')
    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.first_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    # current owner can change his object !!!
    response = self.app.patch_json('{}?acc_token={}'.format(self.request_path, self.first_owner_token),
                                   {"data": {'description': "description 3"}}, status=200)
    self.assertEqual(response.status, '200 OK')

    # Change auth to another owner
    authorization = self.app.authorization
    self.app.authorization = ('Basic', (self.second_owner, ''))

    # create Transfer
    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']
    self.assertIn('date', transfer)
    transfer_creation_date = transfer['date']
    new_access_token = response.json['access']['token']
    new_transfer_token = response.json['access']['transfer']

    # change ownership
    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': self.transfer}})
    self.assertEqual(response.status, '200 OK')
    self.assertNotIn('transfer', response.json['data'])
    self.assertNotIn('transfer_token', response.json['data'])

    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    # New owner can change his object !!!
    response = self.app.patch_json('{}?acc_token={}'.format(self.request_path, new_access_token),
                                   {"data": {'description': "description 4"}}, status=200)
    self.assertEqual(response.status, '200 OK')

    # Object location is stored in Transfer
    response = self.app.get('/transfers/{}'.format(transfer['id']))
    transfer = response.json['data']
    transfer_modification_date = transfer['date']
    self.assertEqual(transfer['usedFor'], self.request_path)
    self.assertNotEqual(transfer_creation_date, transfer_modification_date)

    # try to use already applied transfer
    self.app.authorization = authorization
    collection_path = '/'.join(self.request_path.split('/')[:-1]) + '?acc_token={}'.format(self.acc_token)
    response = self.app.post_json(collection_path, {'data': self.initial_data})
    new_item_id = response.json['data']['id']
    new_request_path = "{}/{}".format(collection_path.split('?')[0], new_item_id)
    access = response.json['access']
    self.app.authorization = ('Basic', (self.second_owner, ''))

    # simulate half-applied transfer activation process (i.e. transfer
    # is successfully applied to a object (tender/auction) and relation is saved in transfer,
    # but object (tender/auction) is not stored with new credentials)
    transfer_doc = self.db.get(transfer['id'])
    transfer_doc['usedFor'] = new_request_path
    self.db.save(transfer_doc)
    response = self.app.post_json('{}/ownership'.format(new_request_path),
                                  {"data": {"id": transfer['id'], 'transfer': access['transfer']}}, status=200)

    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    # broker2 can change the object (tender/auction) (first object (tender/auction) which created in test setup)
    response = self.app.patch_json('{}?acc_token={}'.format(self.request_path, new_access_token),
                                   {"data": {'description': "description 5"}}, status=200)
    self.assertEqual(response.status, '200 OK')
    self.assertNotIn('transfer', response.json['data'])
    self.assertNotIn('transfer_token', response.json['data'])
    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    self.app.authorization = authorization

    # try to use transfer by broker without appropriate accreditation level
    self.app.authorization = ('Basic', (self.invalid_owner, ''))

    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')

    # test level permits to change ownership for 'test' mode
    # first try on non-test object (tender/auction)
    self.app.authorization = ('Basic', (self.test_owner, ''))
    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']

    # set test mode and try to change ownership
    self.app.authorization = ('Basic', ('administrator', ''))
    resource_item = '/'.join(self.request_path.split('/')[:3])
    response = self.app.patch_json(resource_item, {'data': {'mode': 'test'}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['mode'], 'test')

    self.app.authorization = ('Basic', (self.test_owner, ''))
    response = self.app.post_json('{}/ownership'.format(self.request_path),
                                  {"data": {"id": transfer['id'], 'transfer': new_transfer_token}})
    self.assertEqual(response.status, '200 OK')
    if self.owner_check:
        self.assertIn('owner', response.json['data'])
        self.assertEqual(self.test_owner, response.json['data']['owner'])
    else:
        self.assertNotIn('owner', response.json['data'])

    # test accreditation levels are also sepatated
    self.app.authorization = ('Basic', (self.invalid_owner, ''))
    response = self.app.post_json('/transfers', {"data": self.test_transfer_data})
    self.assertEqual(response.status, '201 Created')
    transfer = response.json['data']
