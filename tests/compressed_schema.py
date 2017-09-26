from functools import partial

import graphene
from graphql_to_rest import ExternalRESTField

HOST = 'http://test'


class Faction(graphene.ObjectType):
    base_url = '{}/factions'.format(HOST)

    id = graphene.Int()
    name = graphene.String(name='name')
    heroes = ExternalRESTField(
        partial(lambda: Hero),
        source_field_name='id',
        filter_field_name='faction_id',
    )


class Hero(graphene.ObjectType):
    base_url = '{}/heroes'.format(HOST)
    id = graphene.Int()
    name = graphene.String(name='name')
    faction_id = graphene.Int()
    faction = ExternalRESTField(
        Faction,
        source_field_name='faction_id',
    )
    friend_ids = graphene.List(graphene.Int)
    friends = ExternalRESTField(
        partial(lambda: Hero),
        source_field_name='friend_ids',
        filter_field_name='id',
    )


class Query(graphene.ObjectType):

    factions = ExternalRESTField(
        Faction,
        id=graphene.Argument(graphene.ID),
        is_top_level=True,
    )

    heroes = ExternalRESTField(
        Hero,
        id=graphene.Argument(graphene.ID),
        is_top_level=True,
    )

schema = graphene.Schema(query=Query)
