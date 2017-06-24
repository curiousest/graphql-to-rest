import json
import requests
import graphene


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


class ExternalRESTObject(graphene.ObjectType):

    @classmethod
    def make_request(
            cls,
            base_url,
            query_params,
            data,
            headers,
            resolver_args,
            parent_object,
            filter_by_parent_fields,
            filter_to_source_dict,
            is_list,
            request_method=requests.get,
            *args,
            **kwargs):

        if headers.get('Erase-Headers', False):
            headers = {}
        else:
            del headers['Content-Length']

        if data.get('query', False):
            # remove the graphql query from the data, and pass along the rest
            del data['query']

        # pass along query params from the original request
        query_params.update(resolver_args)

        try:
            id_field = getattr(parent_object, filter_to_source_dict['id'], None)
        except (AttributeError, KeyError, TypeError):
            id_field = None
        if not is_list and id_field is not None and not is_non_str_iterable(id_field):
            # Support retrieve individual object by id in the url (and not query params)
            # Ex: http://some-host/heroes/1/ instead of http://some-host/heroes/?id=1
            base_url = "{}/{}".format(base_url, id_field)
        elif filter_by_parent_fields:
            # this filters nested objects by fields on the parent object.
            # Ex: we don't want to do this for the base Query object (it has no id!)
            cls.update_query_params_from_parent_field_filters(
                parent_object, query_params, filter_to_source_dict
            )

        url = '{}/?{}'.format(base_url, '&'.join([key + '=' + str(value)
                                                  for key, value in query_params.items()]))
        return request_method(url=url, data=data, headers=headers)

    @classmethod
    def update_query_params_from_parent_field_filters(cls, parent_object, query_params, filter_to_source_dict):
        for filter_field, source_field in filter_to_source_dict.items():
            parent_field = getattr(parent_object, source_field)
            if is_non_str_iterable(parent_field):
                # if the data in parent field is a non-string iterable
                query_params[filter_field] = ','.join([str(item)
                                                       for item in getattr(parent_object, source_field)])
            else:
                query_params[filter_field] = parent_field

    @classmethod
    def retrieve_results(cls, json_response, is_list, *args, **kwargs):
        if is_list:
            return json_response['results']
        else:
            return json_response

    @classmethod
    def generate_resolver(
            cls,
            is_list=True,
            filter_to_source_dict=None,
            filter_by_parent_fields=True,
            *class_args, **class_kwargs):

        object_class = cls

        def endpoint_resolver(parent_object, args, context, info):
            headers = dict(context.headers)
            data = json.loads(context.data.decode("utf-8"))
            query_params = [qp.split('=') for qp in context.query_string.decode("utf-8").split("&") if qp]
            # it's hard to optionally get an item from a list in a dictionary comprehension
            query_params = {qp[0]: next(iter(qp[1:]), '') for qp in query_params}

            response = cls.make_request(
                resolver_args=args,
                base_url=object_class.endpoint,
                query_params=query_params,
                data=data,
                headers=headers,
                context=context,
                info=info,
                parent_object=parent_object,
                filter_to_source_dict=filter_to_source_dict,
                filter_by_parent_fields=filter_by_parent_fields,
                is_list=is_list,
                *class_args,
                **class_kwargs
            )

            result = cls.retrieve_results(
                json_response=response.json(),
                resolver_args=args,
                base_url=object_class.endpoint,
                query_params=query_params,
                headers=headers,
                context=context,
                info=info,
                is_list=is_list,
                parent_object=parent_object,
                *class_args,
                **class_kwargs
            )

            return reduce_fields_to_object(object_class, is_list, result)
        return endpoint_resolver
