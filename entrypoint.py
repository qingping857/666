# -*- coding: utf-8 -*-
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# must import
# import robotparser

import scrapy.spiderloader
import scrapy.statscollectors
import scrapy.logformatter
import scrapy.dupefilters
import scrapy.squeues

import scrapy.extensions.spiderstate
import scrapy.extensions.corestats
import scrapy.extensions.telnet
import scrapy.extensions.logstats
import scrapy.extensions.memusage
import scrapy.extensions.memdebug
import scrapy.extensions.feedexport
import scrapy.extensions.closespider
import scrapy.extensions.debug
import scrapy.extensions.httpcache
import scrapy.extensions.statsmailer
import scrapy.extensions.throttle

import scrapy.core.scheduler
import scrapy.core.engine
import scrapy.core.scraper
import scrapy.core.spidermw
import scrapy.core.downloader

import scrapy.downloadermiddlewares.stats
import scrapy.downloadermiddlewares.httpcache
import scrapy.downloadermiddlewares.cookies
import scrapy.downloadermiddlewares.useragent
import scrapy.downloadermiddlewares.httpproxy
import scrapy.downloadermiddlewares.ajaxcrawl
import scrapy.downloadermiddlewares.defaultheaders
import scrapy.downloadermiddlewares.downloadtimeout
import scrapy.downloadermiddlewares.httpauth
import scrapy.downloadermiddlewares.httpcompression
import scrapy.downloadermiddlewares.redirect
import scrapy.downloadermiddlewares.retry
import scrapy.downloadermiddlewares.robotstxt

import scrapy.spidermiddlewares.depth
import scrapy.spidermiddlewares.httperror
import scrapy.spidermiddlewares.offsite
import scrapy.spidermiddlewares.referer
import scrapy.spidermiddlewares.urllength

import scrapy.pipelines

import scrapy.core.downloader.handlers.http
import scrapy.core.downloader.contextfactory

import tkinter as tk
from tkinter import messagebox
import pymysql
import custom_mysql

pymysql.install_as_MySQLdb()

from urllib import parse


class DbConfigWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title('Database Configuration')
        self.window.geometry('400x250+150+150')

        # Host
        self.label_host = tk.Label(self.window, text='Host:')
        self.label_host.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.entry_host = tk.Entry(self.window, width=30)
        self.entry_host.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        self.entry_host.insert(0, "localhost")

        # User
        self.label_user = tk.Label(self.window, text='User:')
        self.label_user.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.entry_user = tk.Entry(self.window, width=30)
        self.entry_user.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        self.entry_user.insert(0, "root")

        # Password
        self.label_pwd = tk.Label(self.window, text='Password:')
        self.label_pwd.grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.entry_pwd = tk.Entry(self.window, width=30, show='*')
        self.entry_pwd.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

        # Database
        self.label_db = tk.Label(self.window, text='Database:')
        self.label_db.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        self.entry_db = tk.Entry(self.window, width=30)
        self.entry_db.grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)
        self.entry_db.insert(0, "sam_gov_data")

        # Port
        self.label_port = tk.Label(self.window, text='Port:')
        self.label_port.grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        self.entry_port = tk.Entry(self.window, width=30)
        self.entry_port.grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)
        self.entry_port.insert(0, "3306")

        # Save button
        self.btn_save = tk.Button(
            self.window,
            text='Save',
            command=self.save_config
        )
        self.btn_save.grid(row=5, column=0, columnspan=2, pady=10)

        # Set modal behavior
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)

    def save_config(self):
        # Test connection
        try:
            con = pymysql.connect(
                host=self.entry_host.get(),
                user=self.entry_user.get(),
                password=self.entry_pwd.get(),
                port=int(self.entry_port.get()),
                charset='utf8mb4'
            )
            con.close()

            # Save to settings
            settings = get_project_settings()
            settings.set('MYSQL_HOST', self.entry_host.get())
            settings.set('MYSQL_USER', self.entry_user.get())
            settings.set('MYSQL_PASSWORD', self.entry_pwd.get())
            settings.set('MYSQL_DB', self.entry_db.get())
            settings.set('MYSQL_PORT', int(self.entry_port.get()))

            messagebox.showinfo("Success", "Database connection successful! Configuration saved.")
            self.window.destroy()

        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to database: {str(e)}")


class GuiCrawler():
    def __init__(self) -> None:
        self.searchType = '8A'
        self.window = tk.Tk()
        self.window.title('Sam crawler')
        self.window.geometry('750x350+100+100')

        self.label1 = tk.Label(self.window, text='page number')
        self.label1.grid(row=0, column=0, pady=10)

        self.label2 = tk.Label(self.window, text='page size')
        self.label2.grid(row=0, column=2, pady=10)

        self.entry1 = tk.Entry(self.window)
        self.entry1.grid(row=0, column=1, sticky=tk.NSEW, pady=10)

        self.entry2 = tk.Entry(self.window)
        self.entry2.grid(row=0, column=3, sticky=tk.NSEW, pady=10)

        self.label3 = tk.Label(self.window, text='params')
        self.label3.grid(row=1, column=0, padx=10, pady=10)

        self.entry3 = tk.Entry(self.window)
        self.entry3.grid(row=1, column=1, columnspan=3, sticky=tk.NSEW, pady=10)

        self.text1 = tk.Text(self.window, height=10)
        self.text1.grid(row=2, column=0, columnspan=4, padx=10)

        btn = tk.Button(
            self.window,
            text='crawler 8A',
            command=self.startCrawl8A
        )
        btn.grid(row=3, column=0)

        btn = tk.Button(
            self.window,
            text='crawler Source Sought or Presolicitation',
            command=self.startCrawlRP
        )
        btn.grid(row=3, column=1)

        btn = tk.Button(
            self.window,
            text='crawler solicitation',
            command=self.startCrawlO
        )
        btn.grid(row=3, column=2)

        btn = tk.Button(
            self.window,
            text='crawler WOSB or EDWOSB',
            command=self.startCrawlWOSB
        )
        btn.grid(row=3, column=3)

        # Add database config button
        db_config_btn = tk.Button(
            self.window,
            text='Database Config',
            command=self.open_db_config
        )
        db_config_btn.grid(row=4, column=0, columnspan=4, pady=10)

        self.entry1.insert(0, "1")
        self.entry2.insert(0, "200")

        self.text1.insert('end', 'You can change the above parameters to fit your demand.\n')
        self.text1.insert('end', 'Page number should be a positive number, start from 1.\n')
        self.text1.insert('end', 'Page size should be a positive number, start from 1.\n')
        self.text1.insert('end', 'Params size should be a serious keywords, split by space.\n')
        self.text1.insert('end',
                          'If the keyword contains the spaces, please enclose the keyword in double quotation marks. \n')
        self.text1.insert('end',
                          'Results will now be saved to MySQL database instead of Excel. Click "Database Config" to set connection details.\n')

        # Check and set database config
        try:
            self.init_db_config()
        except Exception as e:
            self.text1.insert('end', f'Warning: Database not configured properly: {str(e)}\n')

        self.window.mainloop()

    def init_db_config(self):
        # Try to initialize default database settings
        settings = get_project_settings()
        if not settings.get('MYSQL_HOST'):
            settings.set('MYSQL_HOST', 'localhost')
            settings.set('MYSQL_USER', 'root')
            settings.set('MYSQL_PASSWORD', '')
            settings.set('MYSQL_DB', 'sam_gov_data')
            settings.set('MYSQL_PORT', 3306)

    def open_db_config(self):
        DbConfigWindow(self.window)

    def startCrawl8A(self):
        self.searchType = '8A'
        self.startCrawl()

    def startCrawlRP(self):
        self.searchType = 'RP'
        self.startCrawl()

    def startCrawlO(self):
        self.searchType = 'O'
        self.startCrawl()

    def startCrawlWOSB(self):
        self.searchType = 'WOSB'
        self.startCrawl()

    def startCrawl(self):
        self.page = -1
        try:
            self.page = int(self.entry1.get())
            if self.page <= 0:
                self.text1.insert('end', 'Please input correct page number(>0)\n')
                return
        except:
            self.text1.insert('end', 'Please input correct page number(>0)\n')
            return

        self.size = 0
        try:
            self.size = int(self.entry2.get())
            if self.size <= 0:
                self.text1.insert('end', 'Please input correct page size(>0)\n')
                return
        except:
            self.text1.insert('end', 'Please input correct page size(>0)\n')
            return

        self.param = ''
        try:
            self.param = self.entry3.get()
        except:
            self.text1.insert('end', 'Please input correct param\n')
            return

        print('page: {}, size: {}'.format(self.page, self.size))
        self.text1.insert('end',
                          'Current crawl parameter: Page {}, {} per page, Param: {}\n'.format(self.page, self.size,
                                                                                              self.param))

        # 使用subprocess启动新进程运行爬虫
        import subprocess
        import sys

        cmd = [
            sys.executable, 'run_crawler.py',
            str(self.page), str(self.size), self.param, self.searchType
        ]

        self.text1.insert('end', f'启动爬虫: {self.searchType}\n')
        self.text1.insert('end', f'数据将保存到MySQL数据库\n')
        subprocess.Popen(cmd)  # 使用Popen而不是call，这样不会阻塞GUI


gui = GuiCrawler()