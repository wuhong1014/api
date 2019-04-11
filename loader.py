#coding:utf-8
import csv
import json
import os
from utils.log import logger
from utils import exceptions
import yaml
from utils.config import Conf
logger=logger()
conf = Conf('./conf/conf.ini')
TESTS_DIR=conf.get_value('data_addr','case_addr')

def _file_format_check(file, content):
    '''
    校验yaml/yml/json文件的格式
    :param file:
    :param content:
    :return:
    '''
    if not content:
        err_msg = 'file content is empty : {}'.format(file)
        logger.error(err_msg)
        raise  exceptions.FileFormatError(err_msg)
    elif not isinstance(content, (list, dict)):
        err_msg = 'file content does farmat testcase format,must be list or dict : {}'.format(file)
        logger.error(err_msg)
        raise exceptions.FileFormatError(err_msg)
def read_csv(csv_file):
    '''
    :param csv_file:
    :return: list
    :exp:[{},{}]
    '''
    with open(csv_file,'r',encoding='utf-8') as csv_c:
        reader=csv.DictReader(csv_c)
        csv_content = [dict(row) for row in reader]
    return csv_content
def read_yaml(yaml_file):
    '''
    :param yaml_file:
    :return:[{},{}] or {}
    '''
    with open(yaml_file,encoding='utf-8') as yaml_c:
        yaml_content=yaml.safe_load(yaml_c)
        _file_format_check(yaml_file,yaml_content)
        return yaml_content
def read_json(json_file):
    '''
    :param json_file:
    :return: [{},{}] or {}
    '''
    with open(json_file,encoding='utf-8') as json_c:
        try:
            json_content=json.load(json_c)
        except json.JSONDecodeError:
            err_msg = 'json file format error : {}'.format(json_file)
            logger.error(err_msg)
            raise exceptions.FileFormatError(err_msg)
        _file_format_check(json_file,json_content)
        return json_content
def load_file(file):
    '''
    :param file:
    :return:  [{},{}] or {}
    '''
    if not os.path.isfile(file):
        raise FileNotFoundError('{} does not exist!'.format(file))
    file_suffix = os.path.splitext(file)[1].lower()
    if file_suffix == '.json':
        return read_json(file)
    elif file_suffix == '.csv':
        return read_csv(file)
    elif file_suffix in ['.yaml', '.yml']:
        return read_yaml(file)
    else:
        err_msg = 'unsupported file : {}'.format(file)
        logger.error(err_msg)
        return []
def load_folder_files(folder, curdir=False):
    '''
    load type in (yaml/yaml/json) files from folders
    :param folder: str,can be list
    :param curdir: only load curdir files
    :return: list
    '''
    if isinstance(folder, list):
        files = []
        for f in set(folder):
            files.extend(load_folder_files(f, curdir))
        return files
    if not os.path.exists(folder):
        return []
    file_list = []
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            if filename.endswith(('.json', '.yaml', '.yml')):
                file_list.append(os.path.join(dirpath, filename))
        if curdir:
            break
    return file_list
def __extend_with_api_ref(raw_testinfo):
    api_path = raw_testinfo['api']
    if not os.path.exists(api_path):
        if  os.path.exists(os.path.join(TESTS_DIR,api_path)):
            api_path=os.path.join(TESTS_DIR,api_path)
        else:
            raise  FileNotFoundError('{} not found !'.format(api_path))
    raw_testinfo['api_def'] = load_file(api_path)
def __extend_with_suite_ref(raw_testinfo):
    suite_path = raw_testinfo['suite']
    if not os.path.exists(suite_path):
        if  os.path.exists(os.path.join(TESTS_DIR,suite_path)):
            suite_path=os.path.join(TESTS_DIR,suite_path)
        else:
            raise  FileNotFoundError('{} not found !'.format(suite_path))
    raw_testinfo['suite_def'] = format_suite_content(load_file(suite_path))
def __extend_with_testcase_ref(raw_testinfo):
    testcase_path = raw_testinfo['testcase']
    if not os.path.exists(testcase_path):
        if  os.path.exists(os.path.join(TESTS_DIR,testcase_path)):
            testcase_path=os.path.join(TESTS_DIR,testcase_path)
        else:
            raise  FileNotFoundError('{} not found !'.format(testcase_path))
    raw_testinfo['testcase_def'] = format_testcase_content(load_file(testcase_path))
def load_full_test_info(raw_testinfo):
    """ load testcase step content.
            teststep maybe defined directly, or reference api/testcase.

        Args:
            raw_testinfo (dict): test data, maybe in 3 formats.
                # api reference
                {
                    "name": "add product to cart",
                    "api": "/path/to/api",
                    "variables": {},
                    "validate": [],
                    "extract": {}
                }

                # testcase reference
                {
                    "name": "add product to cart",
                    "testcase": "/path/to/testcase",
                    "variables": {}
                }
                # define directly
                {
                    "name": "checkout cart",
                    "request": {},
                    "variables": {},
                    "validate": [],
                    "extract": {}
                }

        Returns:
            dict: loaded teststep content

        """
    # reference api
    if "api" in raw_testinfo:
        __extend_with_api_ref(raw_testinfo)
    # reference testcase
    elif "testcase" in raw_testinfo:
        __extend_with_testcase_ref(raw_testinfo)
    elif 'suite' in raw_testinfo:
        __extend_with_suite_ref(raw_testinfo)
    # define directly
    else:
        pass
    return raw_testinfo
def format_suite_content(suite_content):
    '''
    :param suite_content:  from a suite file，like [{api:xxx},{api:xxx}]
    :return: {
        suite:[api1,api2]
    }
    '''
    apis=[]
    for item in suite_content:
        key,value =item.popitem()
        if  key == 'api':
            apis.append(load_full_test_info(value))
        else:
            logger.warning("unexpected key :{}, key should only be  'api'.".format(key))
    return {"suite":apis}
def format_testcase_content(testcase_content):
    '''
    :param testcase_content:  from a testcase file
    :return: {
        config:{},
        teststeps:[teststep1,teststep2]
    }
    '''
    config = {}
    teststeps = []
    for item in testcase_content:
        key, value = item.popitem()
        if key == 'config':
            config.update(value)
        elif key == 'test':
            teststeps.append(load_full_test_info(value))
        else:
            logger.warning("unexpected key :{}, key should only be 'config' or 'test'.".format(key))
    return {"config": config, "teststeps": teststeps}
def format_testsuite_content(testsuite_content):
    '''
    :param testsuite_content:  from a testsuite file
    :return: {
        config:{},
        testcases:[testcase1,testcase2]
    }
    '''
    config = {}
    testcases = []
    for item in testsuite_content:
        key, value = item.popitem()
        if key == 'config':
            config.update(value)
        elif key == 'testcase':
            testcases.append(load_full_test_info(value))
        else:
            logger.warning("unexpected key :{}, key should only be 'config' or 'test'.".format(key))
    return {"config": config, "testcases": testcases}
def load_test_file(file_path):
    '''
    load test file, file maybe testcase/testsuite/suite/api
    :param path:
    :return: [{
                name:xxx
                path:xxx
                type:api
                request:xxx
            },
            {
                name:xxx
                path:xxx
                type:suite
                apis:xxx
            },
            {
                name:xxx
                config:xxx
                type:testcase
                teststeps:xxx
            },
            {
                name:xxx
                config:xxx
                type:testsuite
                testcases:xxx
            }
            ]
    '''
    raw_content = load_file(file_path)
    loaded_content = {}
    if isinstance(raw_content, dict):

        if 'request' in raw_content:
            # file_type : api
            loaded_content = raw_content
            loaded_content['type'] = 'api'
            loaded_content['path'] = file_path
        else:
            # invaild content
            logger.warning('invalid test file : {}'.format(file_path))
    elif isinstance(raw_content, list) and len(raw_content) > 0:
        key_list = []
        for content in raw_content:
            for k, v in content.items():
                key_list.append(k)
        if 'test' in key_list:
            # file_type : testcase
            loaded_content = format_testcase_content(raw_content)
            loaded_content["path"] = file_path
            loaded_content["type"] = "testcase"
        elif 'api' in key_list:
            # file_type : suite
            loaded_content = format_suite_content(raw_content)
            loaded_content['type'] = 'suite'
            loaded_content['path'] = file_path
        elif 'testcase' in key_list:
            # file_type : testsuite
            loaded_content = format_testsuite_content(raw_content)
            loaded_content['type'] = 'testsuite'
            loaded_content['path'] = file_path
        else:
            # invaild content
            logger.warning('invalid test file : {}'.format(file_path))
    else:
        # invaild content
        logger.warning('invalid test file : {}'.format(file_path))
    return loaded_content
def load_tests(path):
    '''
    :param test_content:path msut be a file path
    :return:dict  :tests mapping ,include testcases and testsuites
        {
            "testcases":[
                {
                  "config":{}
                    "teststep":[{}]
                },
                {...}
            ],
            "testsuites":[
                {
                    "config":{}
                    "testcases":[
                        "testcase1":{},
                        "testcase2":{}
                    ]
                },
                {...}
        }
    '''
    tests_mapping={}
    if not os.path.isabs(path):
        path=os.path.join(TESTS_DIR,path)
    if not os.path.exists(path):
        logger.error("path not found :{} ".format(path))
        raise FileNotFoundError("path not found :{} ".format(path))
    def __load_file_content(path):
        loaded_content = load_test_file(path)
        if not loaded_content:
            pass
        elif loaded_content["type"] == "testsuite":
            tests_mapping.setdefault("testsuites", []).append(loaded_content)
        elif loaded_content["type"] == "testcase":
            tests_mapping.setdefault("testcases", []).append(loaded_content)
        elif loaded_content["type"] == "suite":
            tests_mapping.setdefault("suites", []).append(loaded_content)
        elif loaded_content["type"] == "api":
            tests_mapping.setdefault("apis", []).append(loaded_content)

    if os.path.isdir(path):
        files_list = load_folder_files(path)
        for path in files_list:
            __load_file_content(path)

    elif os.path.isfile(path):
        __load_file_content(path)

    return tests_mapping


if __name__=='__main__':
    # file= r'd:\api\test'
    csv_file=r'd:/api/test/testcases'
    print(load_tests(csv_file))
