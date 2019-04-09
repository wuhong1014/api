#coding:utf-8
import pymysql
from utils.log import logger
logger=logger()
class Mysql:
    def __init__(self,host,port,user,password,db):
        try:
            self.conn=pymysql.Connect(host=host,port=port,user=user,passwd=password,db=db,charset='UTF8')
        except Exception as e:
            logger.error('Connect Fail:'+str(e))
            self.conn=None
    def query(self,sql):
        res=()
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            res=cursor.fetchall()
        except Exception as e:
            logger.info('mysql query error :' +str(e))
        cursor.close()
        #返回结果为（（），（））
        return res
    def modify(self,sql):
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            self.conn.commit()
        except Exception as e:
            logger.error('mysql modify error :'+str(e))
            self.conn.rollback()
        cursor.close()

if  __name__=="__main__":
    mysql=Mysql('127.0.0.1',3306,'root','wh5869358','autotest')
    print(mysql.query("select * from api_test"))
    mysql.conn.close()