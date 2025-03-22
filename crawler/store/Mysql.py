

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.mysql import insert

from ..settings import MYSQL_CONFIG
from ..templates import *


class MysqlConnect():

    def __init__(self) -> None:

        self.mysql_config = MYSQL_CONFIG

        self.engine = create_engine('mysql://{}:{}@{}:{}/{}?charset=utf8'.format(
            self.mysql_config.get('user'),
            self.mysql_config.get('password'),
            self.mysql_config.get('hostname'),
            self.mysql_config.get('port'),
            self.mysql_config.get('database')
        ), echo=True)  # 连接数据库
        self.session = sessionmaker(bind=self.engine)
        self.sess = self.session()
        base = declarative_base()
        #动态创建orm类,必须继承Base, 这个表名是固定的,如果需要为每个爬虫创建一个表,请使用process_item中的
        self.model = {}

        self.model['notelist'] = type('notelist', (base, NotelistTemplate), {
            '__tablename__': 'app_notelist'})

        self.model['noticebid'] = type('noticebid', (base, GetNoticeBidTemplate), {
            '__tablename__': 'app_noticebid'})

        self.model['noticewin'] = type('noticewin', (base, GetNoticeWinTemplate), {
            '__tablename__': 'app_noticewin'})

    def find(self, tablename):
        # 寻找记录
        existing = self.sess.query(self.model[tablename]).all()
        return existing

    def sess(self):
        return self.sess
