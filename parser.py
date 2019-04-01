# encoding: utf-8

import ast
import os
import re
from utils  import exceptions
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

        if func_name in ["parameterize", "P"]:
            if len(args) != 1 or kwargs:
                raise exceptions.ParamsError("P() should only pass in one argument!")
            from utils import loader
            eval_value = loader.load_csv_file(args[0])

        else:
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
    content={
                'request': {
                    'url': '/api/users/$uid',
                    'headers': {'token': '$token'}
                }
            }
    variables_mapping={"$uid":1000,"$token":'X#$%^&CBD'}
    print(substitute_variables(content,variables_mapping))

