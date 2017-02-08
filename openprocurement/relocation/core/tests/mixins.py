from openprocurement.relocation.core.tests.base import test_transfer_data


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

    def prepare_ownership_change(self):
        pass

    def check_permission(self, path, token):
        pass


    def test_change_ownership(self):
        self.prepare_ownership_change()

        # Check owner for object !!!
        response = self.app.get('{}?acc_token={}'.format(self.request_path, self.first_owner_token))
        self.assertEqual(response.status, '200 OK')
        if 'owner' in response.json['data']:
            self.assertEqual(response.json['data']['owner'], self.first_owner)

        # current owner can change his object !!!
        response = self.check_permission(self.request_path, self.first_owner_token)
        self.assertEqual(response.status, '200 OK')

        # Change auth to another owner
        authorization = self.app.authorization
        self.app.authorization = ('Basic', (self.second_owner, ''))

        # other broker can't change the object
        response = self.check_permission(self.request_path, self.first_owner_token)
        self.assertEqual(response.status, '403 Forbidden')

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
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
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        if 'owner' in response.json['data']:
            self.assertEqual(self.second_owner, response.json['data']['owner'])

        # New owner can change his object !!!
        response = self.check_permission(self.request_path, new_access_token)
        self.assertEqual(response.status, '200 OK')

        # Object location is stored in Transfer
        response = self.app.get('/transfers/{}'.format(transfer['id']))
        transfer = response.json['data']
        transfer_modification_date = transfer['date']
        self.assertEqual(transfer['usedFor'], self.request_path)
        self.assertNotEqual(transfer_creation_date, transfer_modification_date)

        # try to use already applied transfer
        self.app.authorization = authorization
        collection_path = '/'.join(self.request_path.split('/')[:-1])
        if hasattr(self, 'create_token'):
            collection_path += '?acc_token={}'.format(self.create_token)
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
        if 'owner' in response.json['data']:
            self.assertEqual(self.second_owner, response.json['data']['owner'])

        # broker2 can change the object (tender/auction) (first object (tender/auction) which created in test setup)
        response = self.check_permission(self.request_path, new_access_token)
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        if 'owner' in response.json['data']:
            self.assertEqual(response.json['data']['owner'], self.second_owner)

        self.app.authorization = authorization
        # old ownfer now can`t change object (tender/auction)
        response = self.check_permission(self.request_path, new_access_token)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('{}/ownership'.format(self.request_path),
                                      {"data": {"id": 'fake id', 'transfer': 'fake transfer'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # try to use transfer by broker without appropriate accreditation level
        self.app.authorization = ('Basic', (self.invalid_owner, ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

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
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
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
        if 'owner' in response.json['data']:
            self.assertEqual(response.json['data']['owner'], self.test_owner)

        # test accreditation levels are also sepatated
        self.app.authorization = ('Basic', (self.invalid_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
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
