#coding:utf-8
from utils import log,exceptions
logger=log.logger()
def query_json(json_content,query,delimiter='.'):
    '''
    >>>Examples:
    >>>json_content = {
        "ids": [1, 2, 3, 4],
        "person": {
            "name": {
                "first_name": "Leo",
                "last_name": "Lee",
            },
            "age": 29,
            "cities": ["Guangzhou", "Shenzhen"]
        }
    }
    >>>
    >>> query_json(json_content, "person.name.first_name")
    >>> Leo
    >>>
    >>> query_json(json_content, "person.name.first_name.0")
    >>> L
    >>>
    >>> query_json(json_content, "person.cities.0")
    >>> Guangzhou


    '''
    raise_flag = False
    response_body = u"response body: {}\n".format(json_content)
    try:
        for key in query.split(delimiter):
            if isinstance(json_content, (list, str)):
                json_content = json_content[int(key)]
            elif isinstance(json_content, dict):
                json_content = json_content[key]
            else:
                logger.log_error(
                    "invalid type value: {}({})".format(json_content, type(json_content)))
                raise_flag = True
    except (KeyError, ValueError, IndexError):
        raise_flag = True

    if raise_flag:
        err_msg = u"Failed to extract! => {}\n".format(query)
        err_msg += response_body
        logger.log_error(err_msg)
        raise exceptions.ExtractFailure(err_msg)

    return json_content