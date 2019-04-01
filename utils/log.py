#utf-8
import logging
from  utils.config import Conf
import os,time
def logger():
    conf=Conf(r'd:\api\conf\conf.ini')
    LOG_DIR=conf.get_value('data_addr','log_addr')
    log_file=time.strftime('%Y%m%d',time.localtime())+'.log'
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    lg=logging.getLogger(__name__)
    lg.setLevel(level=logging.DEBUG)
    #文件输出
    file_hander=logging.FileHandler(os.path.join(LOG_DIR,log_file))
    file_hander.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_hander.setFormatter(formatter)
    lg.addHandler(file_hander)
    #控制台输出
    console_hander=logging.StreamHandler()
    console_hander.setLevel(logging.DEBUG)
    console_hander.setFormatter(formatter)
    lg.addHandler(console_hander)
    return lg

if __name__=='__main__':
    logger=logger()
    logger.debug('hello world!')