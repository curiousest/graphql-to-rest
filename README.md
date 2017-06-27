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
from functools import partial
import graphene
from graphql_to_rest import ExternalRESTField

class Hero(graphene.ObjectType):
    endpoint = "http://your-host/heroes"
    
    id = graphene.Int()
    name = graphene.String(name='name')

    movies_appeared_in_ids = graphene.List(graphene.Int)
    friends = ExternalRESTField(
        partial(lambda: Movie),
        source_to_filter_dict={'movies_appeared_in_ids': 'id'},
    )


class Movie(graphene.ObjectType):
    endpoint = "http://another-host/movies"
    
    id = graphene.Int()
    name = graphene.String(name='name')


class Query(graphene.ObjectType):

    heroes = ExternalRESTField(
        Hero,
        id=graphene.Argument(graphene.ID),
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
        movies_appeared_in {
            id
            name
        }
    }
}
'''
data = {'query': query}
response = requests.get(
    "http://graphql-app-host/graphql/", 
    data=json.dumps(data), 
    content_type='application/json'
)
print(response.json())

{"data": {
    "heroes": [
        {
            "id": 5,
            "movies_appeared_in": [
                {"id": 1, "name": "Movie Name X"},
                {"id": 2, "name": "Movie Name Y"}
]}]}}

# the request to http://graphql-app-host/graphql makes two requests to the heroes endpoint:
# GET http://your-host/heroes?id=5
# GET http://another-host/movies?id=1,2

```

## Testing

```
py.test
py.test --capture=no # if you want to `import pytest; pytest.set_trace()`
```

## Build next

- [ ] [Quickstart app](https://github.com/curiousest/graphql-to-rest-example)
- [ ] [Resolve nested external fields in batches]()
- 