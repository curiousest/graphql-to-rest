import json
import requests
from functools import partial, reduce

import graphene
from promise import Promise
from promise.dataloader import DataLoader
from graphql_to_rest import reduce_fields_to_objects

HOST = 'http://test'


class Faction(graphene.ObjectType):
    endpoint = '{}/factions'.format(HOST)

    id = graphene.ID()
    name = graphene.String(name='name')
    heroes = graphene.List(
        partial(lambda: Hero)
    )

    def resolve_heroes(self, args, context, info):
        headers = dict(context.headers)

        url = '{}/?faction_id={}'.format(
            Hero.endpoint,
            self.id
        )
        response = requests.get(url, headers=headers)
        return reduce_fields_to_objects(
            object_class=Hero,
            is_list=True,
            json_result=response.json()['results']
        )


class HeroLoader(DataLoader):
    def batch_load_fn(self, friend_ids):
        url = '{}/?id={}'.format(
            Hero.endpoint,
            ','.join([str(id) for id in friend_ids])
        )
        response = requests.get(url, headers=self.headers)
        results = response.json()['results']
        return Promise.resolve(results)

        
class Hero(graphene.ObjectType):
    endpoint = '{}/heroes'.format(HOST)
    data_loader = HeroLoader()

    id = graphene.ID()
    name = graphene.String(name='name')
    faction_id = graphene.Int()
    faction = graphene.Field(Faction)
    friend_ids = graphene.List(graphene.Int)
    friends = graphene.List(partial(lambda: Hero))

    def resolve_faction(self, args, context, info):
        headers = dict(context.headers)

        url = '{}/?id={}'.format(
            Faction.endpoint,
            self.faction_id
        )
        response = requests.get(url, headers=headers)
        return reduce_fields_to_objects(
            object_class=Faction,
            is_list=False,
            json_result=response.json()['results'][0]
        )

    def resolve_friends(self, args, context, info):
        self.data_loader.headers = dict(context.headers)
        heroes_json = self.data_loader.load_many(self.friend_ids)
        return heroes_json.then(self.resolve_friends_promise)

    def resolve_friends_promise(self, heroes_json):
        friends_json = filter(lambda h: h['id'] in self.friend_ids, heroes_json)
        return reduce_fields_to_objects(
            object_class=Hero, is_list=True, json_result=friends_json
        )


class Query(graphene.ObjectType):

    factions = graphene.List(
        Faction,
        id=graphene.Argument(graphene.ID)
    )

    heroes = graphene.List(
        Hero,
        id=graphene.Argument(graphene.ID)
    )

    def resolve_factions(self, args, context, info):
        headers = dict(context.headers)
        # if you wanted to pass data along to future requests, you'd have to
        # do this in each resolve method
        data = json.loads(context.data.decode("utf-8"))
        del data['query']

        # if you wanted to pass query params along to future requests,
        # you'd have to do this in each method
        query_params = [qp.split('=')
                        for qp
                        in context.query_string.decode("utf-8").split("&")
                        if qp]
        query_params = {qp[0]: next(iter(qp[1:]), '')
                        for qp in query_params}
        query_params['id'] = args['id']

        url = '{}/?{}'.format(
            Faction.endpoint,
            '&'.join([key + '=' + str(value)
                      for key, value in query_params.items()])
        )

        response = requests.get(url, data=data, headers=headers)
        return reduce_fields_to_objects(
            object_class=Faction,
            is_list=True,
            json_result=response.json()['results']
        )

    def resolve_heroes(self, args, context, info):
        headers = dict(context.headers)

        url = '{}/?id={}'.format(
            Hero.endpoint,
            args['id']
        )
        response = requests.get(url, headers=headers)
        return reduce_fields_to_objects(
            object_class=Hero,
            is_list=True,
            json_result=response.json()['results']
        )

schema = graphene.Schema(query=Query)
