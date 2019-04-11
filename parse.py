# encoding: utf-8

import ast
import os
import re
from utils  import exceptions
from utils.utils import ensure_mapping_format, deepcopy_dict, extend_variables, build_url, extend_validators
import loader
variable_regexp = r"\$([\w_]+)"
function_regexp = r"\$\{([\w_]+\([\$\w\.\-/_ =,]*\))\}"
function_regexp_compile = re.compile(r"^([\w_]+)\(([\$\w\.\-/_ =,]*)\)$")


def parse_string_value(str_value):
    """ parse string to number if possible
    e.g. "123" => 123
         "12.2" => 12.3
         "abc" => "abc"
         "0000" => "0000"
         "$var" => "$var"
    """
    try:
        res = ast.literal_eval(str_value)
        if str_value.startswith('0') and isinstance(res,int):
            res = str_value
        return res
    except ValueError:
        return str_value
    except SyntaxError:
        # e.g. $var, ${func}
        return str_value


def extract_variables(content):
    '''
    extract all variables from str content
    :param content:
    :return:
    e.g:
    ->extract_variables("$var")
    ->return:["var"]
    '''
    try:
        return re.findall(variable_regexp, content)
    except TypeError:
        return []


def extract_functions(content):
    '''
        extract all variables from str content
        :param content:
        :return:
        e.g:
        ->extract_variables("${var()}")
        ->return:["var()"]
        '''
    try:
        return re.findall(function_regexp, content)
    except TypeError:
        return []


def parse_function(content):
    '''
    parser  name , args,kwargs from str  function
    :param content:
    :return:
    e.g:
        ->parser_function("func(a,b,c=1)")
        ->return:
        {
            "func_name":"func",
            "args"=["a","b"],
            "kwargs"={"c":1}
        }
    '''
    matched = function_regexp_compile.match(content)
    if not matched:
        raise exceptions.FunctionNotFound('{} not found function!'.format(content))
    function = {
        "func_name": matched.group(1),
        "args": [],
        "kwargs": {}
    }
    args_str = matched.group(2).strip()
    if not args_str:
        return function
    for arg in args_str.split(','):
        arg=arg.strip()
        if '=' in arg:
            k, v =arg.split('=')
            function["kwargs"][k.strip()]=parse_string_value(v.strip())
        else:
            function["args"].append(parse_string_value(arg))
    return function

def parse_validator(validator):
    """ parse validator

    Args:
        validator (dict): validator maybe in two formats:

            format1: this is kept for compatiblity with the previous versions.
                {"check": "status_code", "comparator": "eq", "expect": 201}
                {"check": "$resp_body_success", "comparator": "eq", "expect": True}
            format2: recommended new version
                {'eq': ['status_code', 201]}
                {'eq': ['$resp_body_success', True]}

    Returns
        dict: validator info

            {
                "check": "status_code",
                "expect": 201,
                "comparator": "eq"
            }

    """
    if not isinstance(validator, dict):
        raise exceptions.ParamsError("invalid validator: {}".format(validator))

    if "check" in validator and len(validator) > 1:
        # format1
        check_item = validator.get("check")

        if "expect" in validator:
            expect_value = validator.get("expect")
        elif "expected" in validator:
            expect_value = validator.get("expected")
        else:
            raise exceptions.ParamsError("invalid validator: {}".format(validator))

        comparator = validator.get("comparator", "eq")

    elif len(validator) == 1:
        # format2
        comparator = list(validator.keys())[0]
        compare_values = validator[comparator]

        if not isinstance(compare_values, list) or len(compare_values) != 2:
            raise exceptions.ParamsError("invalid validator: {}".format(validator))

        check_item, expect_value = compare_values

    else:
        raise exceptions.ParamsError("invalid validator: {}".format(validator))

    return {
        "check": check_item,
        "expect": expect_value,
        "comparator": comparator
    }

def substitute_variables(content, variables_mapping):
    """ substitute variables in content with variables_mapping

    Args:
        content (str/dict/list/numeric/bool/type): content to be substituted.
        variables_mapping (dict): variables mapping.

    Returns:
        substituted content.

    Examples:
        >>> content = {
                'request': {
                    'url': '/api/users/$uid',
                    'headers': {'token': '$token'}
                }
            }
        >>> variables_mapping = {"$uid": 1000}
        >>> substitute_variables(content, variables_mapping)
            {
                'request': {
                    'url': '/api/users/1000',
                    'headers': {'token': '$token'}
                }
            }

    """
    if isinstance(content, (list, set, tuple)):
        return [
            substitute_variables(item, variables_mapping)
            for item in content
        ]

    if isinstance(content, dict):
        substituted_data = {}
        for key, value in content.items():
            eval_key = substitute_variables(key, variables_mapping)
            eval_value = substitute_variables(value, variables_mapping)
            substituted_data[eval_key] = eval_value

        return substituted_data

    if isinstance(content, str):
        # content is in string format here
        for var, value in variables_mapping.items():
            if content == var:
                # content is a variable
                content = value
            else:
                if not isinstance(value, str):
                    value = str(value)
                content = content.replace(var, value)

    return content

#
# def parse_parameters(parameters, variables_mapping=None, functions_mapping=None):
#     pass
#
#
def get_mapping_variable(variable_name, variables_mapping):
    """ get variable from variables_mapping.

    Args:
        variable_name (str): variable name
        variables_mapping (dict): variables mapping

    Returns:
        mapping variable value.

    Raises:
        exceptions.VariableNotFound: variable is not found.

    """
    try:
        return variables_mapping[variable_name]
    except KeyError:
        raise exceptions.VariableNotFound("{} is not found.".format(variable_name))


def get_mapping_function(function_name, functions_mapping):
    """ get function from functions_mapping,
    Args:
        variable_name (str): variable name
        variables_mapping (dict): variables mapping
    Returns:
        mapping function object.

    """
    try:
        return functions_mapping[function_name]

    except (NameError, TypeError):
        raise exceptions.FunctionNotFound("{} is not found.".format(function_name))


def parse_string_functions(content, variables_mapping, functions_mapping):
    """ parse string content with functions mapping.

    Args:
        content (str): string content to be parsed.
        variables_mapping (dict): variables mapping.
        functions_mapping (dict): functions mapping.

    Returns:
        str: parsed string content.

    Examples:
        >>> content = "abc${add_one(3)}def"
        >>> functions_mapping = {"add_one": lambda x: x + 1}
        >>> parse_string_functions(content, functions_mapping)
            "abc4def"

    """
    functions_list = extract_functions(content)
    for func_content in functions_list:
        function_meta = parse_function(func_content)
        func_name = function_meta["func_name"]

        args = function_meta.get("args", [])
        kwargs = function_meta.get("kwargs", {})
        args = parse_data(args, variables_mapping, functions_mapping)
        kwargs = parse_data(kwargs, variables_mapping, functions_mapping)


        func = get_mapping_function(func_name, functions_mapping)
        eval_value = func(*args, **kwargs)

        func_content = "${" + func_content + "}"
        if func_content == content:
            # content is a function, e.g. "${add_one(3)}"
            content = eval_value
        else:
            # content contains one or many functions, e.g. "abc${add_one(3)}def"
            content = content.replace(
                func_content,
                str(eval_value), 1
            )

    return content


def parse_string_variables(content, variables_mapping, functions_mapping):
    """ parse string content with variables mapping.

    Args:
        content (str): string content to be parsed.
        variables_mapping (dict): variables mapping.

    Returns:
        str: parsed string content.

    Examples:
        >>> content = "/api/users/$uid"
        >>> variables_mapping = {"$uid": 1000}
        >>> parse_string_variables(content, variables_mapping, {})
            "/api/users/1000"

    """
    variables_list = extract_variables(content)
    for variable_name in variables_list:
        variable_value = get_mapping_variable(variable_name, variables_mapping)

        if variable_name == "request" and isinstance(variable_value, dict) \
            and "url" in variable_value and "method" in variable_value:
            # call setup_hooks action with $request
            for key, value in variable_value.items():
                variable_value[key] = parse_data(
                    value,
                    variables_mapping,
                    functions_mapping
                )
            parsed_variable_value = variable_value
        elif "${}".format(variable_name) == variable_value:
            # variable_name = "token"
            # variables_mapping = {"token": "$token"}
            parsed_variable_value = variable_value
        else:
            parsed_variable_value = parse_data(
                variable_value,
                variables_mapping,
                functions_mapping
            )

        # TODO: replace variable label from $var to {{var}}
        if "${}".format(variable_name) == content:
            # content is a variable
            content = parsed_variable_value
        else:
            # content contains one or several variables
            if not isinstance(parsed_variable_value, str):
                parsed_variable_value = str(parsed_variable_value)

            content = content.replace(
                "${}".format(variable_name),
                parsed_variable_value, 1
            )

    return content


def parse_data(content, variables_mapping=None, functions_mapping=None, raise_if_variable_not_found=True):
    """ parse content with variables mapping

    Args:
        content (str/dict/list/(int/float)/bool/type): content to be parsed
        variables_mapping (dict): variables mapping.
        functions_mapping (dict): functions mapping.
        raise_if_variable_not_found (bool): if set False, exception will not raise when VariableNotFound occurred.

    Returns:
        parsed content.

    Examples:
        >>> content = {
                'request': {
                    'url': '/api/users/$uid',
                    'headers': {'token': '$token'}
                }
            }
        >>> variables_mapping = {"uid": 1000, "token": "abcdef"}
        >>> parse_data(content, variables_mapping)
            {
                'request': {
                    'url': '/api/users/1000',
                    'headers': {'token': 'abcdef'}
                }
            }

    """

    if content is None or isinstance(content, (int, float, bool, type)):
        return content

    if isinstance(content, (list, set, tuple)):
        return [
            parse_data(
                item,
                variables_mapping,
                functions_mapping,
                raise_if_variable_not_found
            )
            for item in content
        ]

    if isinstance(content, dict):
        parsed_content = {}
        for key, value in content.items():
            parsed_key = parse_data(
                key,
                variables_mapping,
                functions_mapping,
                raise_if_variable_not_found
            )
            parsed_value = parse_data(
                value,
                variables_mapping,
                functions_mapping,
                raise_if_variable_not_found
            )
            parsed_content[parsed_key] = parsed_value

        return parsed_content

    if isinstance(content, (str,bytes)):
        # content is in string format here
        variables_mapping = variables_mapping or {}
        functions_mapping = functions_mapping or {}
        content = content.strip()

        try:
            # replace functions with evaluated value
            # Notice: parse_string_functions must be called before parse_string_variables
            content = parse_string_functions(
                content,
                variables_mapping,
                functions_mapping
            )
            # replace variables with binding value
            content = parse_string_variables(
                content,
                variables_mapping,
                functions_mapping
            )
        except exceptions.VariableNotFound:
            if raise_if_variable_not_found:
                raise

    return content
def __parse_config(config, project_mapping):
    """ parse testcase/testsuite config, include variables and name.
    """
    # get config variables
    raw_config_variables = config.pop("variables", {})
    raw_config_variables_mapping = ensure_mapping_format(raw_config_variables)
    override_variables = deepcopy_dict(project_mapping.get("variables", {}))
    functions = project_mapping.get("functions", {})

    # override config variables with passed in variables
    raw_config_variables_mapping.update(override_variables)

    # parse config variables
    parsed_config_variables = {}
    for key, value in raw_config_variables_mapping.items():
        parsed_value = parse_data(
            value,
            raw_config_variables_mapping,
            functions,
            raise_if_variable_not_found=False
        )
        parsed_config_variables[key] = parsed_value

    if parsed_config_variables:
        config["variables"] = parsed_config_variables

    # parse config name
    config["name"] = parse_data(
        config.get("name", ""),
        parsed_config_variables,
        functions
    )

    # parse config base_url
    if "base_url" in config:
        config["base_url"] = parse_data(
            config["base_url"],
            parsed_config_variables,
            functions
        )
def _extend_with_testcase(test_dict, testcase_def_dict):
    """ extend test with testcase definition
        test will merge and override testcase config definition.

    Args:
        test_dict (dict): test block
        testcase_def_dict (dict): testcase definition

    Returns:
        dict: extended test dict.

    """
    # override testcase config variables
    testcase_def_dict["config"].setdefault("variables", {})
    testcase_def_variables = ensure_mapping_format(testcase_def_dict["config"].get("variables", {}))
    testcase_def_variables.update(test_dict.pop("variables", {}))
    testcase_def_dict["config"]["variables"] = testcase_def_variables

    # override base_url, verify
    # priority: testcase config > testsuite tests
    test_base_url = test_dict.pop("base_url", "")
    if not testcase_def_dict["config"].get("base_url"):
        testcase_def_dict["config"]["base_url"] = test_base_url

    test_verify = test_dict.pop("verify", True)
    testcase_def_dict["config"].setdefault("verify", test_verify)

    # override testcase config name, output, etc.
    testcase_def_dict["config"].update(test_dict)

    test_dict.clear()
    test_dict.update(testcase_def_dict)


def _extend_with_api(test_dict, api_def_dict):
    """ extend test with api definition, test will merge and override api definition.

    Args:
        test_dict (dict): test block
        api_def_dict (dict): api definition

    Returns:
        dict: extended test dict.

    Examples:
        >>> api_def_dict = {
                "name": "get token 1",
                "request": {...},
                "validate": [{'eq': ['status_code', 200]}]
            }
        >>> test_dict = {
                "name": "get token 2",
                "extract": {"token": "content.token"},
                "validate": [{'eq': ['status_code', 201]}, {'len_eq': ['content.token', 16]}]
            }
        >>> _extend_with_api(test_dict, api_def_dict)
            {
                "name": "get token 2",
                "request": {...},
                "extract": {"token": "content.token"},
                "validate": [{'eq': ['status_code', 201]}, {'len_eq': ['content.token', 16]}]
            }

    """
    # override name
    api_def_name = api_def_dict.pop("name", "")
    test_dict["name"] = test_dict.get("name") or api_def_name

    # override variables
    def_variables = api_def_dict.pop("variables", [])
    test_dict["variables"] = extend_variables(
        def_variables,
        test_dict.get("variables", {})
    )

    # merge & override validators TODO: relocate
    def_raw_validators = api_def_dict.pop("validate", [])
    ref_raw_validators = test_dict.get("validate", [])
    def_validators = [
        parse_validator(validator)
        for validator in def_raw_validators
    ]
    ref_validators = [
        parse_validator(validator)
        for validator in ref_raw_validators
    ]
    test_dict["validate"] = extend_validators(
        def_validators,
        ref_validators
    )

    # merge & override extractors
    def_extrators = api_def_dict.pop("extract", {})
    test_dict["extract"] = extend_variables(
        def_extrators,
        test_dict.get("extract", {})
    )

    # TODO: merge & override request
    test_dict["request"] = api_def_dict.pop("request", {})

    # base_url & verify: priority api_def_dict > test_dict
    if api_def_dict.get("base_url"):
        test_dict["base_url"] = api_def_dict["base_url"]

    if "verify" in api_def_dict:
        test_dict["request"]["verify"] = api_def_dict["verify"]

    # merge & override setup_hooks
    def_setup_hooks = api_def_dict.pop("setup_hooks", [])
    ref_setup_hooks = test_dict.get("setup_hooks", [])
    extended_setup_hooks = list(set(def_setup_hooks + ref_setup_hooks))
    if extended_setup_hooks:
        test_dict["setup_hooks"] = extended_setup_hooks
    # merge & override teardown_hooks
    def_teardown_hooks = api_def_dict.pop("teardown_hooks", [])
    ref_teardown_hooks = test_dict.get("teardown_hooks", [])
    extended_teardown_hooks = list(set(def_teardown_hooks + ref_teardown_hooks))
    if extended_teardown_hooks:
        test_dict["teardown_hooks"] = extended_teardown_hooks

    # TODO: extend with other api definition items, e.g. times
    test_dict.update(api_def_dict)

    return test_dict
def __parse_testcase_tests(tests, config, project_mapping):
    """ override tests with testcase config variables, base_url and verify.
        test maybe nested testcase.

        variables priority:
        testcase config > testcase test > testcase_def config > testcase_def test > api

        base_url/verify priority:
        testcase test > testcase config > testsuite test > testsuite config > api

    Args:
        tests (list):
        config (dict):
        project_mapping (dict):

    """
    config_variables = config.pop("variables", {})
    config_base_url = config.pop("base_url", "")
    config_verify = config.pop("verify", True)
    functions = project_mapping.get("functions", {})

    for test_dict in tests:

        # base_url & verify: priority test_dict > config
        if (not test_dict.get("base_url")) and config_base_url:
            test_dict["base_url"] = config_base_url

        test_dict.setdefault("verify", config_verify)

        # 1, testcase config => testcase tests
        # override test_dict variables
        test_dict["variables"] = extend_variables(
            test_dict.pop("variables", {}),
            config_variables
        )
        test_dict["variables"] = parse_data(
            test_dict["variables"],
            test_dict["variables"],
            functions,
            raise_if_variable_not_found=False
        )

        # parse test_dict name
        test_dict["name"] = parse_data(
            test_dict.pop("name", ""),
            test_dict["variables"],
            functions,
            raise_if_variable_not_found=False
        )

        if "testcase_def" in test_dict:
            # test_dict is nested testcase

            # 2, testcase test_dict => testcase_def config
            testcase_def = test_dict.pop("testcase_def")
            _extend_with_testcase(test_dict, testcase_def)

            # 3, testcase_def config => testcase_def test_dict
            _parse_testcase(test_dict, project_mapping)
        elif "suite_def" in test_dict:
            suite_def = test_dict.pop("suite_def")
            test_dict.clear()
            test_dict.update(suite_def)

            _parse_suite(test_dict)

        else:
            if "api_def" in test_dict:
                # test_dict has API reference
                # 2, test_dict => api
                api_def_dict = test_dict.pop("api_def")
                _extend_with_api(test_dict, api_def_dict)

            if test_dict.get("base_url"):
                # parse base_url
                base_url = parse_data(
                    test_dict.pop("base_url"),
                    test_dict["variables"],
                    functions
                )

                # build path with base_url
                # variable in current url maybe extracted from former api
                request_url = parse_data(
                    test_dict["request"]["url"],
                    test_dict["variables"],
                    functions,
                    raise_if_variable_not_found=False
                )
                test_dict["request"]["url"] = build_url(
                    base_url,
                    request_url
                )


def _parse_testcase(testcase, project_mapping):
    """ parse testcase

    Args:
        testcase (dict):
            {
                "config": {},
                "teststeps": []
            }

    """
    testcase.setdefault("config", {})
    __parse_config(testcase["config"], project_mapping)
    __parse_testcase_tests(testcase["teststeps"], testcase["config"], project_mapping)
def _parse_suite(suite):
    """ parse suite

    Args:
        suite (dict):
            {

                "suite": []
            }

    """
    for api in suite["suite"]:
        if "api_def" in api.keys():
            api_def=api.pop("api_def")
            _extend_with_api(api,api_def)

def __get_parsed_testsuite_testcases(testcases, testsuite_config):
    """ override testscases with testsuite config variables, base_url and verify.

        variables priority:
        parameters > testsuite config > testcase config > testcase_def config > testcase_def tests > api

        base_url priority:
        testcase_def tests > testcase_def config > testcase config > testsuite config

    Args:
        testcases (dict):
            {
                "testcase1 name": {
                    "testcase": "testcases/create_and_check.yml",
                    "weight": 2,
                    "variables": {
                        "uid": 1000
                    },
                    "parameters": {
                        "uid": [100, 101, 102]
                    },
                    "testcase_def": {
                        "config": {},
                        "teststeps": []
                    }
                },
                "testcase2 name": {}
            }
        testsuite_config (dict):
            {
                "name": "testsuite name",
                "variables": {
                    "device_sn": "${gen_random_string(15)}"
                },
                "base_url": "http://127.0.0.1:5000"
            }


    """
    testsuite_base_url = testsuite_config.get("base_url")
    testsuite_config_variables = testsuite_config.get("variables", {})
    parsed_testcase_list = []

    for testcase_name, testcase in testcases.items():

        parsed_testcase = testcase.pop("testcase_def")
        parsed_testcase.setdefault("config", {})
        parsed_testcase["path"] = testcase["testcase"]
        parsed_testcase["config"]["name"] = testcase_name

        if "weight" in testcase:
            parsed_testcase["config"]["weight"] = testcase["weight"]

        # base_url priority: testcase config > testsuite config
        parsed_testcase["config"].setdefault("base_url", testsuite_base_url)

        # 1, testsuite config => testcase config
        # override test_dict variables
        testcase_config_variables = extend_variables(
            testcase.pop("variables", {}),
            testsuite_config_variables
        )

        # 2, testcase config > testcase_def config
        # override testcase_def config variables
        parsed_testcase_config_variables = extend_variables(
            parsed_testcase["config"].pop("variables", {}),
            testcase_config_variables
        )

        # parse config variables
        parsed_config_variables = {}
        for key, value in parsed_testcase_config_variables.items():
            try:
                parsed_value = parse_data(
                    value,
                    parsed_testcase_config_variables,
                )
            except exceptions.VariableNotFound:
                pass
            parsed_config_variables[key] = parsed_value

        if parsed_config_variables:
            parsed_testcase["config"]["variables"] = parsed_config_variables
        else:
            parsed_testcase_list.append(parsed_testcase)

    return parsed_testcase_list
def _parse_testsuite(testsuite, project_mapping):
    testsuite.setdefault("config", {})
    __parse_config(testsuite["config"], project_mapping)
    parsed_testcase_list = __get_parsed_testsuite_testcases(
        testsuite["testcases"],
        testsuite["config"],
        project_mapping
    )
    return parsed_testcase_list
def parse_tests(tests_mapping):
    """ parse tests and load to parsed testcases
        tests include api, testcases and testsuites.

    Args:
        tests_mapping (dict): project info and testcases list.

            {

                "testsuites": [
                    {   # testsuite data structure
                        "config": {},
                        "testcases": {
                            "testcase1 name": {
                                "variables": {
                                    "uid": 1000
                                },
                                "parameters": {
                                    "uid": [100, 101, 102]
                                },
                                "testcase_def": {
                                    "config": {},
                                    "teststeps": []
                                }
                            },
                            "testcase2 name": {}
                        }
                    }
                ],
                "testcases": [
                    {   # testcase data structure
                        "config": {
                            "name": "desc1",
                            "path": "testcase1_path",
                            "variables": {},                # optional, priority 2
                        },
                        "teststeps": [
                            # test data structure
                            {
                                'name': 'test step desc1',
                                'variables': [],            # optional, priority 3
                                'extract': [],
                                'validate': [],
                                'api_def': {
                                    "variables": {}         # optional, priority 4
                                    'request': {},
                                }
                            },
                            test_dict_2   # another test dict
                        ]
                    },
                    testcase_dict_2     # another testcase dict
                ],
                "api": {
                    "variables": {},
                    "request": {}
                }
            }

    """
    project_mapping = tests_mapping.get("project_mapping", {})
    parsed_tests_mapping = {
        "project_mapping": project_mapping,
        "testcases": []
    }

    for test_type in tests_mapping:

        if test_type == "testsuites":
            # load testcases of testsuite
            testsuites = tests_mapping["testsuites"]
            for testsuite in testsuites:
                parsed_testcases = _parse_testsuite(testsuite, project_mapping)
                for parsed_testcase in parsed_testcases:
                    parsed_tests_mapping["testcases"].append(parsed_testcase)

        elif test_type == "testcases":
            for testcase in tests_mapping["testcases"]:
                _parse_testcase(testcase, project_mapping)
                parsed_tests_mapping["testcases"].append(testcase)

        elif test_type == "apis":
            # encapsulate api as a testcase
            for api_content in tests_mapping["apis"]:
                testcase = {
                    "teststeps": [api_content]
                }
                _parse_testcase(testcase, project_mapping)
                parsed_tests_mapping["testcases"].append(testcase)

    return parsed_tests_mapping
if __name__ == '__main__':

    # import re
    # # print(re.findall(function_regexp_compile,"var()"))
    # import re
    #
    # text = "JGood is a hand你some boy, he is cool, clever, and so on..."
    # m = re.search(r'\shan(\w+)o(m)e\s', text)
    # if m:
    #
    #     print(m.group(), m.group(1), m.group(2))
    # else:
    #     print('not search')


    import  loader

    csv_file = r'd:/api/test/testcases'
    loader_data=loader.load_tests(csv_file)
    print(parse_tests(loader_data))