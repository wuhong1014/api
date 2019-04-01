#coding:utf-8
''' 发邮件 '''
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from .log import logger
logger = logger()


def send_email(mailconf,sender,receivers,subject,att):
    #创建一个带附件的实例
    message=MIMEMultipart()
    message['From']=Header('管理员','utf-8')
    message['Subject']=Header(subject,'utf-8')
    #邮件正文
    with open(att,'rb') as f:
        att_content=f.read()
    message.attach(MIMEText(att_content,'html','utf-8'))
    #构造附件
    att1 = MIMEText(att_content,'base64','utf-8')
    att1["Content-Type"] = 'application/octet-stream'
    att1["Content-Disposition"] = 'attachment; filename="%s"'%(os.path.basename(att))
    message.attach(att1)

    try:
        if  mailconf['mail_host']=='smtp.qq.com':
            smtpObj = smtplib.SMTP_SSL()
        else:
            smtpObj = smtplib.SMTP()
        smtpObj.connect(mailconf['mail_host'], int(mailconf['mail_port']))  # 25 为 SMTP 端口号
        smtpObj.login(mailconf['mail_user'], mailconf['mail_pass'])
        smtpObj.sendmail(sender, receivers, message.as_string())
        logger.info("邮件发送成功")
    except smtplib.SMTPException as e:
        logger.error("Error: 无法发送邮件\n %s"%str(e))