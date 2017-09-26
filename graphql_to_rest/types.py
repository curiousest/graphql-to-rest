import functools
import inspect
import json
import requests
from copy import copy

import graphene
from promise import Promise
from promise.dataloader import DataLoader
from flask import request

def is_non_str_iterable(obj):
    return type(obj) != str and hasattr(obj, '__iter__')


def reduce_fields_to_objects(object_class, json_result, is_list=True):
    if is_list:
        return [object_class(**{key: value
                                for key, value in individual_result.items()
                                if key in object_class._meta.fields})
                for individual_result in json_result]
    else:
        fields = {key: value for key, value in json_result.items()
                  if key in object_class._meta.fields}
    return object_class(**fields)


def get_actual_object_class(obj):
    '''
    Classes are often passed as functools.partial(lambda: X) in order to allow
    lazy evaluation of types (self-referential, etc).
    '''
    if inspect.isfunction(obj) or type(obj) is functools.partial:
        return obj()
    return obj


class RequestMaker():

    def __init__(self, filter_by_parent_fields=True, filter_field_name=None, forward_headers=True, forward_data=True, forward_query_params=True, request_method=requests.get):
        self.filter_by_parent_fields = filter_by_parent_fields
        self.forward_headers = forward_headers
        self.forward_data = forward_data
        self.forward_query_params = forward_query_params
        self.filter_field_name = filter_field_name
        self.filter_values = None
        self.request_method = request_method

    def initialize_headers(self):
        self.headers = dict(self.headers)

    def initialize_data(self):
        self.data = json.loads(self.data.decode("utf-8"))

    def initialize_query_params(self):
        query_params = [qp.split('=')
                        for qp
                        in self.query_string.decode("utf-8").split("&")
                        if qp]
        # it's hard to optionally get an item from a list in a
        # dictionary comprehension
        self.query_params = {qp[0]: next(iter(qp[1:]), '')
                             for qp in query_params}

    def generate_headers_for_request(self):
        if self.headers.get('Erase-Headers', False) and not self.forward_headers:
            headers = {}
        else:
            headers = copy(self.headers)
            del headers['Content-Length']
        return headers

    def generate_data_for_request(self):
        if not self.headers.get('Erase-Data', False) and self.forward_data:
            if self.data.get('query', False):
                # remove the graphql query from the data, and pass along the rest
                del self.data['query']
        else:
            data = {}

    def generate_url_for_request(self):
        query_params = self.generate_query_params()
        query_string = '&'.join([key + '=' + str(value)
                                 for key, value in query_params.items()])
        return '{}/?{}'.format(self.base_url, query_string)

    def generate_query_params(self):
        query_params = self.query_params
        if not self.forward_query_params:
            query_params = {}

        ''' if not self.headers.get('Erase-Query-Params', False):
            # pass along query params from the original request
            query_params.update(self.resolver_args)
        '''
        query_params.update(self.graphql_arguments)

        # for downstream filtering by id
        if self.filter_by_parent_fields:
            query_params[self.filter_field_name] = self.generate_filter_value()

        return query_params

    def generate_filter_value(self):
        assert self.filter_values is not None
        if is_non_str_iterable(self.filter_values):
            filter_value = ','.join(
                [str(item) for item in self.filter_values]
            )
        else:
            filter_value = self.filter_values
        return filter_value
    
    def make_request(self, *args, **kwargs):
        self.initialize_data()
        self.initialize_headers()
        self.initialize_query_params()

        response =  self.request_method(
            url=self.generate_url_for_request(),
            data=self.generate_data_for_request(), 
            headers=self.generate_headers_for_request()
        )
        return response


class ExternalRESTField(graphene.Field):

    def __init__(self, rest_object_class, source_field_name='id', filter_field_name='id', is_top_level=False, *args, **kwargs):
        assert is_top_level or not (source_field_name == 'id' and filter_field_name == 'id') 
        self.source_field_name = source_field_name
        self.filter_field_name = filter_field_name
        self.rest_object_class = rest_object_class
        self.is_top_level = is_top_level

        self.request_maker = RequestMaker(
            filter_by_parent_fields=(not is_top_level),
            filter_field_name=filter_field_name
        )

        def batch_load_fn(source_values):
            self.request_maker.filter_values = source_values
            response = self.request_maker.make_request()
            return Promise.resolve(response.json()['results'])

        self.data_loader = DataLoader(batch_load_fn)

        super().__init__(graphene.List(rest_object_class), *args, **kwargs)

    def get_resolver(self, parent_resolver):
        if self.resolver:
            return self.resolver
        else:
            return self.generate_resolver(get_actual_object_class(self.rest_object_class))
    
    def generate_resolver(self, rest_object_class, *class_args, **class_kwargs):

        def endpoint_resolver_promise(parent_object, results):            
            relevant_results = filter(lambda h: h['id'] in getattr(parent_object, self.source_field_name), results)
            return reduce_fields_to_objects(rest_object_class, relevant_results)

        def endpoint_resolver(parent_object, args, context, info):

            # This is called for every parent object where we want nested objects.
            # Therefore we don't want to do unnecessary computation (ex:
            # processing query params/headers from the original request)
            # Instead, we do initial processing in request_maker.initialize_x
            # and final processing in request_maker.generate_x
            self.request_maker.headers = context.headers
            self.request_maker.data = context.data
            self.request_maker.base_url = rest_object_class.base_url
            self.request_maker.query_string = context.query_string
            self.request_maker.graphql_arguments = args
            
            if self.is_top_level:
                response = self.request_maker.make_request()
                return reduce_fields_to_objects(rest_object_class, response.json()['results'])
            else:
                source_values = getattr(parent_object, self.source_field_name)
                if not is_non_str_iterable(source_values):
                    source_values = [source_values]
                result = self.data_loader.load_many(source_values)
                return result.then(
                    functools.partial(endpoint_resolver_promise, parent_object)
                )

        return endpoint_resolver
