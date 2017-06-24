from functools import partial

import graphene

from src.external_rest import ExternalRESTObject

HOST = 'http://test'


class Faction(ExternalRESTObject):
    endpoint = '{}/factions'.format(HOST)

    id = graphene.Int()
    name = graphene.String(name='name')
    heroes = graphene.List(
        partial(lambda: Hero),
        resolver=partial(lambda *args, **kwargs: Hero.generate_resolver(
            filter_to_source_dict={'faction_id': 'id'}, is_list=True
        )(*args, **kwargs))
    )


class Hero(ExternalRESTObject):
    endpoint = '{}/heroes'.format(HOST)
    id = graphene.Int()
    name = graphene.String(name='name')
    faction_id = graphene.Int()
    faction = graphene.Field(
        Faction,
        resolver=Faction.generate_resolver(
            filter_to_source_dict={'id': 'faction_id'}, is_list=False
        )
    )
    friend_ids = graphene.List(graphene.Int)
    friends = graphene.List(
        partial(lambda: Hero),
        resolver=partial(lambda *args, **kwargs: Hero.generate_resolver(
            filter_to_source_dict={'id': 'friend_ids'}, is_list=True
        )(*args, **kwargs))
    )


class Query(graphene.ObjectType):

    factions = graphene.List(
        Faction,
        id=graphene.Argument(graphene.ID),
        resolver=Faction.generate_resolver(filter_by_parent_fields=False)
    )

    heroes = graphene.List(
        Hero,
        id=graphene.Argument(graphene.ID),
        resolver=Hero.generate_resolver(filter_by_parent_fields=False)
    )

schema = graphene.Schema(query=Query)
