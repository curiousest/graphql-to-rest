import json
import requests
from functools import partial

import graphene
from promise import Promise
from promise.dataloader import DataLoader
from graphql_to_rest import reduce_fields_to_object

HOST = 'http://test'


class Faction(graphene.ObjectType):
    endpoint = '{}/factions'.format(HOST)

    id = graphene.Int()
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
        return reduce_fields_to_object(
            object_class=Hero,
            is_list=True,
            json_result=response.json()['results']
        )


class HeroLoader(DataLoader):
    def batch_load_fn(self, keys):
        import pytest; pytest.set_trace()
        return Promise.resolve(keys)
hero_loader = HeroLoader()

class Hero(graphene.ObjectType):
    endpoint = '{}/heroes'.format(HOST)
    id = graphene.Int()
    name = graphene.String(name='name')
    faction_id = graphene.Int()
    faction = graphene.Field(Faction)
    friend_ids = graphene.List(graphene.Int)
    friends = graphene.List(partial(lambda: Hero))

    def resolve_faction(self, args, context, info):
        headers = dict(context.headers)

        url = '{}/{}/'.format(
            Faction.endpoint,
            self.faction_id
        )
        response = requests.get(url, headers=headers)
        return reduce_fields_to_object(
            object_class=Faction,
            is_list=False,
            json_result=response.json()
        )

    def resolve_friends(self, args, context, info):
        headers = dict(context.headers)

        url = '{}/?id={}'.format(
            Hero.endpoint,
            ','.join([str(id) for id in self.friend_ids])
        )
        return hero_loader.load_many(self.friend_ids)
        response = requests.get(url, headers=headers)
        return reduce_fields_to_object(
            object_class=Hero,
            is_list=True,
            json_result=response.json()['results']
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
        return reduce_fields_to_object(
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
        return reduce_fields_to_object(
            object_class=Hero,
            is_list=True,
            json_result=response.json()['results']
        )

schema = graphene.Schema(query=Query)
