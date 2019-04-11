import os,time
from utils.config import Conf
cur_path = os.path.dirname(__file__)

print(os.path.join(cur_path,'report/'+time.strftime('%Y%m%d',time.localtime())+'_api_report.html'))
# if not os.path.exists(LOG_DIR):
#     os.makedirs(LOG_DIR)

# configparser.NoOptionError
# configparser.NoSectionError