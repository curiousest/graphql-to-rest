import json
import requests
from functools import partial

import graphene

from src.external_rest import reduce_fields_to_object

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

        url = '{}/?id={}'.format(
            Faction.endpoint,
            args['id']
        )
        response = requests.get(url, headers=headers)
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
