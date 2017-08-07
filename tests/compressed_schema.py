from functools import partial

import graphene
from graphql_to_rest import ExternalRESTField

HOST = 'http://test'


class Faction(graphene.ObjectType):
    endpoint = '{}/factions'.format(HOST)

    id = graphene.Int()
    name = graphene.String(name='name')
    heroes = ExternalRESTField(
        partial(lambda: Hero),
        source_to_filter_dict={'id': 'faction_id'},
    )


class Hero(graphene.ObjectType):
    endpoint = '{}/heroes'.format(HOST)
    id = graphene.Int()
    name = graphene.String(name='name')
    faction_id = graphene.Int()
    faction = ExternalRESTField(
        Faction,
        retrieve_by_id_field='faction_id',
    )
    friend_ids = graphene.List(graphene.Int)
    friends = ExternalRESTField(
        partial(lambda: Hero),
        source_to_filter_dict={'friend_ids': 'id'},
    )


class Query(graphene.ObjectType):

    factions = ExternalRESTField(
        Faction,
        id=graphene.Argument(graphene.ID),
        top_level=True
    )

    heroes = ExternalRESTField(
        Hero,
        id=graphene.Argument(graphene.ID),
    )

schema = graphene.Schema(query=Query)
