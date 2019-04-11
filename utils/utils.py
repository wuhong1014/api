#coding:utf-8
import collections
import copy
import json
import re

from utils import log,exceptions
from utils.exceptions import ParamsError

logger=log.logger()
def omit_long_data(body, omit_len=512):
    """ omit too long str/bytes
    """
    if not isinstance(body, str):
        return body

    body_len = len(body)
    if body_len <= omit_len:
        return body

    omitted_body = body[0:omit_len]

    appendix_str = " ... OMITTED {} CHARACTORS ...".format(body_len - omit_len)
    if isinstance(body, bytes):
        appendix_str = appendix_str.encode("utf-8")

    return omitted_body + appendix_str

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
def ensure_mapping_format(variables):
    """ ensure variables are in mapping format.

    Args:
        variables (list/dict): original variables

    Returns:
        dict: ensured variables in dict format

    Examples:
        >>> variables = [
                {"a": 1},
                {"b": 2}
            ]
        >>> print(ensure_mapping_format(variables))
            {
                "a": 1,
                "b": 2
            }

    """
    if isinstance(variables, list):
        variables_dict = {}
        for map_dict in variables:
            variables_dict.update(map_dict)

        return variables_dict

    elif isinstance(variables, dict):
        return variables

    else:
        raise exceptions.ParamsError("variables format error!")
#coding:utf-8
def lower_dict_keys(origin_dict):
    """ convert keys in dict to lower case

    Args:
        origin_dict (dict): mapping data structure

    Returns:
        dict: mapping with all keys lowered.

    Examples:
        >>> origin_dict
        {
            "Name": "",
            "Request": "",
            "URL": "",
            "METHOD": "",
            "Headers": "",
            "Data": ""
        }
        >>> lower_dict_keys(origin_dict)
            {
                "name": "",
                "request": "",
                "url": "",
                "method": "",
                "headers": "",
                "data": ""
            }

    """
    if not origin_dict or not isinstance(origin_dict, dict):
        return origin_dict

    return {
        key.lower(): value
        for key, value in origin_dict.items()
    }
def lower_test_dict_keys(test_dict):
    """ convert keys in test_dict to lower case, convertion will occur in two places:
        1, all keys in test_dict;
        2, all keys in test_dict["request"]
    """
    # convert keys in test_dict
    test_dict = lower_dict_keys(test_dict)

    if "request" in test_dict:
        # convert keys in test_dict["request"]
        test_dict["request"] = lower_dict_keys(test_dict["request"])

    return test_dict
def _convert_validators_to_mapping(validators):
    """ convert validators list to mapping.

    Args:
        validators (list): validators in list

    Returns:
        dict: validators mapping, use (check, comparator) as key.

    Examples:
        >>> validators = [
                {"check": "v1", "expect": 201, "comparator": "eq"},
                {"check": {"b": 1}, "expect": 200, "comparator": "eq"}
            ]
        >>> _convert_validators_to_mapping(validators)
            {
                ("v1", "eq"): {"check": "v1", "expect": 201, "comparator": "eq"},
                ('{"b": 1}', "eq"): {"check": {"b": 1}, "expect": 200, "comparator": "eq"}
            }

    """
    validators_mapping = {}

    for validator in validators:
        if not isinstance(validator["check"], collections.Hashable):
            check = json.dumps(validator["check"])
        else:
            check = validator["check"]

        key = (check, validator["comparator"])
        validators_mapping[key] = validator

    return validators_mapping
def extend_validators(raw_validators, override_validators):
    """ extend raw_validators with override_validators.
        override_validators will merge and override raw_validators.

    Args:
        raw_validators (dict):
        override_validators (dict):

    Returns:
        list: extended validators

    Examples:
        >>> raw_validators = [{'eq': ['v1', 200]}, {"check": "s2", "expect": 16, "comparator": "len_eq"}]
        >>> override_validators = [{"check": "v1", "expect": 201}, {'len_eq': ['s3', 12]}]
        >>> extend_validators(raw_validators, override_validators)
            [
                {"check": "v1", "expect": 201, "comparator": "eq"},
                {"check": "s2", "expect": 16, "comparator": "len_eq"},
                {"check": "s3", "expect": 12, "comparator": "len_eq"}
            ]

    """

    if not raw_validators:
        return override_validators

    elif not override_validators:
        return raw_validators

    else:
        def_validators_mapping = _convert_validators_to_mapping(raw_validators)
        ref_validators_mapping = _convert_validators_to_mapping(override_validators)

        def_validators_mapping.update(ref_validators_mapping)
        return list(def_validators_mapping.values())
def extend_variables(raw_variables, override_variables):
    """ extend raw_variables with override_variables.
        override_variables will merge and override raw_variables.

    Args:
        raw_variables (list):
        override_variables (list):

    Returns:
        dict: extended variables mapping

    Examples:
        >>> raw_variables = [{"var1": "val1"}, {"var2": "val2"}]
        >>> override_variables = [{"var1": "val111"}, {"var3": "val3"}]
        >>> extend_variables(raw_variables, override_variables)
            {
                'var1', 'val111',
                'var2', 'val2',
                'var3', 'val3'
            }

    """
    if not raw_variables:
        override_variables_mapping = ensure_mapping_format(override_variables)
        return override_variables_mapping

    elif not override_variables:
        raw_variables_mapping = ensure_mapping_format(raw_variables)
        return raw_variables_mapping

    else:
        raw_variables_mapping = ensure_mapping_format(raw_variables)
        override_variables_mapping = ensure_mapping_format(override_variables)
        raw_variables_mapping.update(override_variables_mapping)
        return raw_variables_mapping
def deepcopy_dict(data):
    """ deepcopy dict data, ignore file object (_io.BufferedReader)

    Args:
        data (dict): dict data structure
            {
                'a': 1,
                'b': [2, 4],
                'c': lambda x: x+1,
                'd': open('LICENSE'),
                'f': {
                    'f1': {'a1': 2},
                    'f2': io.open('LICENSE', 'rb'),
                }
            }

    Returns:
        dict: deep copied dict data, with file object unchanged.

    """
    try:
        return copy.deepcopy(data)
    except TypeError:
        copied_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                copied_data[key] = deepcopy_dict(value)
            else:
                try:
                    copied_data[key] = copy.deepcopy(value)
                except TypeError:
                    copied_data[key] = value

        return copied_data
absolute_http_url_regexp = re.compile(r"^https?://", re.I)
def build_url(base_url, path):
    """ prepend url with hostname unless it's already an absolute URL """
    if absolute_http_url_regexp.match(path):
        return path
    elif base_url:
        return "{}/{}".format(base_url.rstrip("/"), path.lstrip("/"))
    else:
        raise ParamsError("base url missed!")

