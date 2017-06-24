# graphql-to-REST

Makes any REST API compatible with [GraphQL](http://graphql.org/learn/) requests.

It can:

* Sit as a standalone Flask app in front/behind your authentication layer, somewhere in between your frontend and services' APIs
* Communicate to services/APIs spanning multiple hosts
* Conform to different [opinions](https://cloud.google.com/apis/design/) [of](https://hackernoon.com/restful-api-designing-guidelines-the-best-practices-60e1d954e7c9) [how](https://docs.atlassian.com/jira/REST/cloud/) [REST](https://github.com/Microsoft/api-guidelines/blob/vNext/Guidelines.md) [should](https://docs.stormpath.com/rest/product-guide/latest/reference.html) [work](http://www.vinaysahni.com/best-practices-for-a-pragmatic-restful-api)

It can't:

* Modify data

You must:

* Define your API schema in [graphene](https://github.com/graphql-python/graphene) (example below)
* Run a flask app [like this](https://github.com/curiousest/graphql-to-rest-example) somewhere

## Example Usage

[Here is a repository you can fork and use.](https://github.com/curiousest/graphql-to-rest-example)

### Schema definition

```python
import graphene
from external_rest import ExternalRESTObject

class Hero(ExternalRESTObject):
    endpoint = "http://your-host/heroes"
    
    id = graphene.Int()
    name = graphene.String(name='name')
    friend_ids = graphene.List(graphene.Int)
    friends = graphene.List(
        partial(lambda: Hero),
        resolver=partial(lambda *args, **kwargs: Hero.generate_resolver(
            filter_to_source_dict={'id': 'friend_ids'}, is_list=True
        )(*args, **kwargs))
    )

class Query(graphene.ObjectType):

    heroes = graphene.List(
        Hero,
        id=graphene.Argument(graphene.ID),
        resolver=Hero.generate_resolver(filter_by_parent_fields=False)
    )

schema = graphene.Schema(query=Query)
```

### GraphQL Request / Response

```python
import requests
import json

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
response = requests.get(
    "http://your-host/graphql/", 
    data=json.dumps(data), 
    content_type='application/json'
)
print(response.json())

> {"data":{"heroes":[{"id":5,"friends":[{"id":6,"name":"Obi"},{"id":7,"name":"Yoda"}]}]}}

```

## Testing

```
py.test
py.test --capture=no # if you want to `import pytest; pytest.set_trace()`
```
