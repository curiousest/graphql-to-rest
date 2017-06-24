from flask import Flask
from flask_graphql import GraphQLView

from tests.compressed_schema import schema as schema1
from tests.expressive_schema import schema as schema2


def create_app(path='/graphql', **kwargs):
    app = Flask(__name__)
    app.debug = True
    app.add_url_rule(path + '/compressed', view_func=GraphQLView.as_view('graphql-compressed', schema=schema1, **kwargs))
    app.add_url_rule(path + '/expressive', view_func=GraphQLView.as_view('graphql-expressive', schema=schema2, **kwargs))
    return app


if __name__ == '__main__':
    app = create_app(graphiql=True)
    app.run()
