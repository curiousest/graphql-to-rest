import pytest
import requests_mock
import json


'''
Cases come from http://graphql.org/learn/queries/

Imagine the endpoints:

Heroes
url: /heroes/
filters: id, faction_id
fields: id, name, height, friend_ids, faction_id

ex: GET /heroes/?id=5
[{
    'id': 5,
    'name': 'Luke',
    'height': 1.25,
    'friend_ids': [6, 7],
    'faction_id': 1
}]

Factions
url: /factions/
filters: id
fields: id, name

ex: GET /factions/?id=1
[{
    'id': 1,
    'name': 'jedi',
}]

'''

hero_1_data = {
    'id': 5,
    'name': 'Luke',
    'height': 1.25,
    'friend_ids': [6, 7],
    'faction_id': 1,
}
hero_2_data = {
    'id': 6,
    'name': 'Obi',
    'height': 1.3,
    'friend_ids': [5, 7],
    'faction_id': 1,
}
hero_3_data = {
    'id': 7,
    'name': 'Yoda',
    'height': 0.5,
    'friend_ids': [5, 6],
    'faction_id': 1,
}

faction_1_data = {
    'id': 1,
    'name': 'jedi'
}


class ExternalRESTTestClass:

    def setUp(self):
        assert self.graphql_host is not None, \
            "Subclass this and add a host"

    def test_single_related_field_by_id(self, client):
        query = '''
        {
            heroes (id: "5") {
                id
                faction {
                    id,
                    name
                }
            }
        }
        '''
        data = {'query': query}

        with requests_mock.mock() as m:
            m.get(
                'http://test/heroes/?id=5',
                json={
                    'results': [hero_1_data]
                })
            m.get('http://test/factions/1/', json=faction_1_data)
            response = client.post(
                self.graphql_host,
                data=json.dumps(data),
                content_type='application/json',
            )
        assert response.status_code == 200, "{} error: {}".format(
            response.status_code, response.data
        )
        json_response = json.loads(response.data.decode())
        assert 'errors' not in json_response
        assert json_response['data']['heroes'][0]['id'] == 5
        assert json_response['data']['heroes'][0]['faction']['id'] == 1

    def test_multiple_related_field_by_parent_id(self, client):
        query = '''
        {
            factions (id: "1") {
                id
                name
                heroes {
                    id
                    name
                }
            }
        }
        '''
        data = {'query': query}

        with requests_mock.mock() as m:
            m.get(
                'http://test/factions/?id=1',
                json={
                    'results': [faction_1_data]
                })
            m.get('http://test/heroes/?faction_id=1', json={
                'results': [hero_1_data, hero_2_data, hero_3_data]
            })

            response = client.post(
                self.graphql_host,
                data=json.dumps(data),
                content_type='application/json',
            )

        assert response.status_code == 200, "{} error: {}".format(
            response.status_code, response.data
        )
        json_response = json.loads(response.data.decode())

        assert 'errors' not in json_response
        assert json_response['data']['factions'][0]['id'] == 1
        assert 5 in [a['id']
                     for a in json_response['data']['factions'][0]['heroes']]

    def test_multiple_related_field_by_ids(self, client):
        query = '''
        {
            heroes (id: "5") {
                id
                friends {
                    id
                    name
                }
            }
        }
        '''
        data = {'query': query}

        with requests_mock.mock() as m:
            m.get(
                'http://test/heroes/?id=5',
                json={
                    'results': [hero_1_data]
                })
            m.get('http://test/heroes/?id=6,7', json={
                'results': [hero_2_data, hero_3_data]
            })

            response = client.post(
                self.graphql_host,
                data=json.dumps(data),
                content_type='application/json',
            )
        assert response.status_code == 200, "{} error: {}".format(
            response.status_code, response.data
        )
        json_response = json.loads(response.data.decode())

        assert 'errors' not in json_response, "error: {}".format(
            response.data
        )
        assert json_response['data']['heroes'][0]['id'] == 5
        assert json_response['data']['heroes'][0]['friends'][0]['id'] == 6
        assert json_response['data']['heroes'][0]['friends'][1]['id'] == 7

    def test_passes_query_params(self, client):
        query = '''
        {
            factions (id: "1") {
                id
            }
        }
        '''
        data = {'query': query}

        with requests_mock.mock() as m:
            m.get(
                'http://test/factions/?this_query_param=exists&that_query_param=exists&id=1',
                json={
                    'results': [faction_1_data]
                })
            response = client.post(
                self.graphql_host,
                query_string={
                    'this_query_param': 'exists', 'that_query_param': 'exists'
                },
                data=json.dumps(data),
                content_type='application/json',
            )
        # this will error if the mock get url (with query params) doesn't
        # match what is requested
        requested_query_string = m.request_history[0].query
        assert 'this_query_param=exists' in requested_query_string
        assert 'that_query_param=exists' in requested_query_string

    def test_passes_data(self, client):
        query = '''
        {
            factions (id: "1") {
                id
            }
        }
        '''
        data = {'query': query, 'this_data': 'exists'}

        with requests_mock.mock() as m:
            m.get(
                'http://test/factions/?id=1',
                json={
                    'results': [faction_1_data]
                })
            response = client.post(
                self.graphql_host,
                data=json.dumps(data),
                content_type='application/json',
            )
        # this will error if the mock get url (with query params) doesn't
        # match what is requested
        assert 'this_data' in m.request_history[0].text

    def test_passes_headers(self, client):
        query = '''
        {
            factions (id: "1") {
                id
            }
        }
        '''
        data = {'query': query}

        with requests_mock.mock() as m:
            m.get(
                'http://test/factions/?id=1',
                json={
                    'results': [faction_1_data]
                })
            response = client.post(
                self.graphql_host,
                data=json.dumps(data),
                content_type='application/json',
                headers={'X-THIS-HEADER': 'exists'}
            )
        assert m.request_history[0]._request.headers['X-This-Header'] == 'exists'

    def test_batch_requests(self, client):
        query = '''
        {
            heroes (id: 5) {
                id
                friends {
                    id
                    friends {
                        id
                        name
                    }
                }
            }
        }
        '''
        data = {'query': query}

        with requests_mock.mock() as m:
            m.get('http://test/heroes/?id=5', json={
                'results': [hero_1_data]
            })
            m.get('http://test/heroes/?id=6,7', json={
                'results': [hero_2_data, hero_3_data]
            })
            m.get('http://test/heroes/?id=6,7,5', json={
                'results': [hero_1_data, hero_2_data, hero_3_data]
            })

            response = client.post(
                self.graphql_host,
                data=json.dumps(data),
                content_type='application/json',
            )
            
        assert response.status_code == 200, "{} error: {}".format(
            response.status_code, response.data
        )
        json_response = json.loads(response.data.decode())
        assert 'errors' not in json_response, "error: {}".format(
            response.data
        )
        # This is an upper bound - the results can be cached from previous calls. 
        # When running just this test in the current version of graphene/promises, the following
        # calls are made:
        # http://test/heroes/?id=5
        # http://test/heroes/?id=6,7
        # http://test/heroes/?id=5
        # When running the whole test suite, the following calls are made:
        # http://test/heroes/?id=5
        # http://test/heroes/?id=5
        assert len(m.request_history) <= 3, 'Requests weren`t batched'

        # make sure the json looks roughly correct
        assert 'name' in json_response['data']['heroes'][0]['friends'][0]['friends'][0]
        assert len(json_response['data']['heroes'][0]['friends'][0]['friends']) == 2

'''
class TestCompressedSchema(ExternalRESTTestClass):
    graphql_host = '/graphql/compressed'

''' 
class TestExpressiveSchema(ExternalRESTTestClass):
    # for sanity and comparison, show what ExternalRESTField is doing under the
    # hood using the expressive schema
    graphql_host = '/graphql/expressive'

