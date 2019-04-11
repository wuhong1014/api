# encoding: utf-8
import configparser
import os
import time
import unittest

from utils import exceptions, log, HTMLTestRunner, utils
import loader,parse,runner,validator
from utils.config import Conf

logger=log.logger()
class HttpRunner(object):

    def __init__(self,   report_dir=None,):
        """ initialize HttpRunner.

        Args:

            report_dir (str): html report save directory.
            log_level (str): logging level.

        """
        self.test_loader = unittest.TestLoader()
        self.report_dir = report_dir



    def _add_tests(self, tests_mapping):
        """ initialize testcase with Runner() and add to test suite.

        Args:
            tests_mapping (dict): project info and testcases list.

        Returns:
            unittest.TestSuite()

        """
        def _add_test(test_runner, test_dict):
            """ add test to testcase.
            """
            def test(self):
                try:
                    test_runner.run_test(test_dict)
                except exceptions.BaseFailure as ex:
                    self.fail(str(ex))
                finally:
                    self.meta_datas = test_runner.meta_datas

            if "config" in test_dict:
                # run nested testcase
                test.__doc__ = test_dict["config"].get("name")
            else:
                # run api test
                test.__doc__ = test_dict.get("name")

            return test

        test_suite = unittest.TestSuite()
        functions = tests_mapping.get("project_mapping", {}).get("functions", {})

        for testcase in tests_mapping["testcases"]:
            config = testcase.get("config", {})
            name = config.get("name",'')
            test_runner = runner.Runner(config, functions)
            TestSequense = type(name or "no name case", (unittest.TestCase,), {})

            tests = testcase.get("teststeps", [])
            for index, test_dict in enumerate(tests):
                for times_index in range(int(test_dict.get("times", 1))):
                    # suppose one testcase should not have more than 9999 steps,
                    # and one step should not run more than 999 times.
                    test_method_name = 'test_{:04}_{:03}_{}'.format(index, times_index,test_dict.get("name",""))
                    test_method = _add_test(test_runner, test_dict)
                    setattr(TestSequense, test_method_name, test_method)

            loaded_testcase = self.test_loader.loadTestsFromTestCase(TestSequense)
            setattr(loaded_testcase, "config", config)
            setattr(loaded_testcase, "teststeps", tests)
            setattr(loaded_testcase, "runner", test_runner)
            test_suite.addTest(loaded_testcase)

        return test_suite





    def run_tests(self, tests_mapping):
        """ run testcase/testsuite data
        """
        # parse tests
        parsed_tests_mapping = parse.parse_tests(tests_mapping)

        # add tests to test suite
        test_suite = self._add_tests(parsed_tests_mapping)

        # run test suite
        cur_path = os.path.dirname(__file__)
        conf_path = os.path.join(cur_path, 'conf/conf.ini')
        conf = Conf(conf_path)
        try:
            REPORT_DIR = conf.get_value('data_addr', 'report_addr')
        except (configparser.NoSectionError,configparser.NoOptionError):
            REPORT_DIR=os.path.join(cur_path,'report/')

        if not os.path.exists(REPORT_DIR):
            os.makedirs(REPORT_DIR)

        filename = os.path.join(REPORT_DIR,time.strftime('%Y%m%d%H%M%S',time.localtime())+'_api_report.html') # 定义个报告存放路径，支持相对路径
        f = open(filename, 'wb')  # 结果写入HTML 文件
        runner = HTMLTestRunner.HTMLTestRunner(stream=f, title='api_report', description='Report_description',
                                                 verbosity=2)  # 使用HTMLTestRunner配置参数，输出报告路径、报告标题、描述
        runner.run(test_suite)


    def run_path(self, path):
        """ run testcase/testsuite file or folder.

        Args:
            path (str): testcase/testsuite file/foler path.
        Returns:
            instance: HttpRunner() instance
        """
        # load tests

        tests_mapping = loader.load_tests(path)
        self.run_tests(tests_mapping)

    def run(self, path_or_tests):
        """ main interface.

        Args:
            path_or_tests:
                str: testcase/testsuite file/foler path
                dict: valid testcase/testsuite data

        """
        if validator.is_testcase_path(path_or_tests):
            self.run_path(path_or_tests)
        elif validator.is_testcases(path_or_tests):
            self.run_tests(path_or_tests)
        else:
            raise exceptions.ParamsError("invalid testcase path or testcases.")

if __name__=='__main__':
    runn=HttpRunner()
    runn.run('d:/api/test/testcases')