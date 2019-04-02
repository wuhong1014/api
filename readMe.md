在conf目录中存放的是测试配置相关的文件，配置文件可以使用ini、xml、yml等文件类型。例如，要测试的网址、调试日志的文件名、日志的输出格式等

在data目录下存放所有测试相关的文件,使用yaml,yml,json文件类型。

– 在data/interface目录下，用于存放单个接口的测试数据。

– 在data/suite目录下，用于存放测试套件数据。

在log目录下存放输出日志.log文件。

在report目录下存放测试报告文件html类的文件。

loader.py，加载测试数据，文件用于测试文件内容的读取,返回指定格式的文件内容。

parse.py，用于解析数据

runner.py，执行测试

api_main.py,执行测试的入口

test目录存放测试用例，与data目录关联，xls or xlsx格式，该目录约定excel下sheet名称英文、唯一，遵循python类定义规范：驼峰，sheet名称=测试类class名称，测试编号=test_测试方法名称

在utils目录下存放公共方法。
– utils/assertion.py文件用于添加各种自定义的断言（测试结果和目标结果是否一致的判断），断言失败抛出AssertionError就OK。

– utils/exceptions.py文件用于定义各种异常。

– utils/config.py文件用于项目公共内容配置，以及读取配置文件中的配置。这里配置文件用的yaml，也可用其他如XML,INI等，需在file_reader中添加相应的Reader进行处理。

– utils/extractor.py文件用于抽取器，从响应结果中抽取部分数据，这里实现的是json返回数据的抽取，可以自己添加XML格式、普通字符串格式、Header的抽取器

– utils/generator.py文件用于一些生成器方法，生成随机数，手机号，以及连续数字等，以便使用这些数据进行测试

– utils/HTMLTestRunner.py是一个第三方模块，用于生成html的测试报告。

– utils/log.py文件通过读取配置文件，定义日志级别、日志文件名、日志格式等。

– utils/email.py文件用来给指定用户发送邮件。可指定多个收件人，可带附件。

– utils/support.py文件用来编写一些支持方法，比如签名、加密等
