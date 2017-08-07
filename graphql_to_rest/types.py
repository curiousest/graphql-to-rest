import functools
import inspect
import json
import requests
import graphene
from promise import Promise
from promise.dataloader import DataLoader
from flask import request

def is_non_str_iterable(obj):
    return type(obj) != str and hasattr(obj, '__iter__')


def reduce_fields_to_object(object_class, is_list, json_result):
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


class ExternalRESTDataLoader(DataLoader):

    def use_batched_values(self, context, headers, data, query_params, source_values):
        query_params[context.filter_field_name] = source_values

    def batch_load_fn(self, source_values):
        headers = dict(request.headers)
        data = json.loads(request.data.decode("utf-8"))

        query_params = [qp.split('=')
                        for qp
                        in request.query_string.decode("utf-8").split("&")
                        if qp]
        # it's hard to optionally get an item from a list in a
        # dictionary comprehension
        query_params = {qp[0]: next(iter(qp[1:]), '')
                        for qp in query_params}

        self.use_batched_values(headers, data, query_params, source_values)

        response = cls.make_request(
            resolver_args=args,
            base_url=rest_object_class.endpoint,
            query_params=query_params,
            data=data,
            headers=headers,
            context=context,
            info=info,
            parent_object=parent_object,
            source_to_filter_dict=source_to_filter_dict,
            is_list=is_list,
            *class_args,
            **class_kwargs
        )

        result = cls.retrieve_results(
            json_response=response.json(),
            resolver_args=args,
            base_url=rest_object_class.endpoint,
            query_params=query_params,
            headers=headers,
            context=context,
            info=info,
            is_list=is_list,
            parent_object=parent_object,
            source_to_filter_dict=source_to_filter_dict,
            *class_args,
            **class_kwargs
        )

        return reduce_fields_to_object(rest_object_class, is_list, result)


class ExternalRESTField(graphene.Field):

    def __init__(self, rest_object_class, source_to_filter_dict=None, retrieve_by_id_field=None, is_top_level=False, *args, **kwargs):
        self.source_to_filter_dict = source_to_filter_dict
        self.retrieve_by_id_field = retrieve_by_id_field
        self.is_list = retrieve_by_id_field is None
        self.rest_object_class = rest_object_class
        self.is_top_level = is_top_level

        if self.is_list:
            super().__init__(graphene.List(rest_object_class), *args, **kwargs)
        else:
            super().__init__(rest_object_class, *args, **kwargs)

    def get_resolver(self, parent_resolver):
        if self.resolver:
            return self.resolver
        else:
            return self.generate_resolver(
                get_actual_object_class(self.rest_object_class),
                self.is_list,
                source_to_filter_dict=self.source_to_filter_dict,
                retrieve_by_id_field=self.retrieve_by_id_field,
            )

    @classmethod
    def make_request(
            cls,
            base_url,
            query_params,
            data,
            headers,
            resolver_args,
            parent_object,
            source_to_filter_dict,
            retrieve_by_id_field,
            request_method=requests.get,
            *args,
            **kwargs):

        if not headers.get('Erase-Query-Params', False):
            # pass along query params from the original request
            query_params.update(resolver_args)

        if not headers.get('Erase-Data', False):
            if data.get('query', False):
                # remove the graphql query from the data, and pass along the rest
                del data['query']
        else:
            data = {}

        if headers.get('Erase-Headers', False):
            headers = {}
        else:
            del headers['Content-Length']

        if retrieve_by_id_field:
            # Support retrieve individual object by id in the url
            # (and not query params)
            # Ex: http://some-host/heroes/1/ instead of
            # http://some-host/heroes/?id=1
            base_url = "{}/{}".format(
                base_url,
                getattr(parent_object, retrieve_by_id_field)
            )
        elif source_to_filter_dict:
            # This filters nested objects by fields on the parent object.
            # We don't want to do this for the base Query object
            # (it has no id!)
            cls.update_query_params_from_parent_field_filters(
                parent_object, query_params, source_to_filter_dict
            )

        url = '{}/?{}'.format(
            base_url,
            '&'.join([key + '=' + str(value)
                      for key, value in query_params.items()])
        )
        return request_method(url=url, data=data, headers=headers)

    @classmethod
    def update_query_params_from_parent_field_filters(cls, parent_object, query_params, source_to_filter_dict):
        for source_field, filter_field in source_to_filter_dict.items():
            parent_field = getattr(parent_object, source_field)
            if is_non_str_iterable(parent_field):
                # if the data in parent field is a non-string iterable
                query_params[filter_field] = ','.join(
                    [str(item) for item in getattr(parent_object, source_field)]
                )
            else:
                query_params[filter_field] = parent_field

    @classmethod
    def retrieve_results(cls, json_response, is_list, *args, **kwargs):
        if is_list:
            return json_response['results']
        else:
            return json_response

    @classmethod
    def generate_resolver(cls, rest_object_class, source_to_filter_dict, is_list, *class_args, **class_kwargs):

        def endpoint_resolver_promise(parent_object, args, context, info, field_filters):
            headers = dict(context.headers)
            data = json.loads(context.data.decode("utf-8"))

            query_params = [qp.split('=')
                            for qp
                            in context.query_string.decode("utf-8").split("&")
                            if qp]
            # it's hard to optionally get an item from a list in a
            # dictionary comprehension
            query_params = {qp[0]: next(iter(qp[1:]), '')
                            for qp in query_params}

            response = cls.make_request(
                resolver_args=args,
                base_url=rest_object_class.endpoint,
                query_params=query_params,
                data=data,
                headers=headers,
                context=context,
                info=info,
                parent_object=parent_object,
                source_to_filter_dict=source_to_filter_dict,
                is_list=is_list,
                *class_args,
                **class_kwargs
            )

            result = cls.retrieve_results(
                json_response=response.json(),
                resolver_args=args,
                base_url=rest_object_class.endpoint,
                query_params=query_params,
                headers=headers,
                context=context,
                info=info,
                is_list=is_list,
                parent_object=parent_object,
                source_to_filter_dict=source_to_filter_dict,
                *class_args,
                **class_kwargs
            )

            return reduce_fields_to_object(rest_object_class, is_list, result)

        def endpoint_resolver(parent_object, args, context, info):
            if cls.is_top_level:

            result = cls.data_loader.load(getattr(parent_object, source_field_name))
            result.then(
                functools.partial(endpoint_resolver_promise, cls, args, context, info)
            )

        return endpoint_resolver
