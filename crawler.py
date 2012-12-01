#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import urllib2
import gevent
import time
import datetime
from settings import *
from pyquery import PyQuery
from gevent import Greenlet
from redis_queue import Queue
from rediset import Rediset
from redis import Redis

'''
Rediset can be used in this way
>>> redis = Redis(host='localhost', port=6379)
>>> rs = Rediset(hash_generated_keys=True, redis_client=redis) # these parameters are all optional
>>> s = rs.Set('downloaded_url')
>>> s.add('http://m.sohu.com')
>>> s.remove('http://m.sohu.com')
>>> 'http://m.sohu.com' in s
>>> True
>>> len(s)
'''

try:
    urllib2.socket.setdefaulttimeout(TIMEOUT)
except Exception:
    urllib2.socket.setdefaulttimeout(10)


class RedisQueueException(Exception):
    pass


class LogFileException(Exception):
    pass


class CrawlerEngine:
    '''
    '''

    # variables from settings
    if not 'ROOT_LOG' in globals():
        ROOT_LOG = 'log'
    if not 'DELAY_LOG' in globals():
        DELAY_LOG = 'delay'
    if not 'ERROR_LOG' in globals():
        ERROR_LOG = 'error'
    if not 'REDIS_HOST' in globals():
        REDIS_HOST = 'localhost'
    if not 'REDIS_PORT' in globals():
        REDIS_PORT = 6379
    if not 'CRAWLER_NUMBER' in globals():
        CRAWLER_NUMBER = 2
    if not 'DELAY_TIME' in globals():
        DELAY_TIME = 2

    try:
        delay_logger = open(os.path.join(ROOT_LOG, DELAY_LOG + '.log'), 'a')
        error_logger = open(os.path.join(ROOT_LOG, ERROR_LOG + '.log'), 'a')
    except IOError:
        raise LogFileException, 'Failed to open log file'

    try:
        redis_client = Redis(host=REDIS_HOST, port=int(REDIS_PORT))
    except ValueError, e:
        redis_client = Redis(host=REDIS_HOST, port=6379)
    downloaded_urls = Rediset(hash_generated_keys=True, \
            redis_client=redis_client).Set('downloaded_urls')


    def __init__(self, start_urls):
        if not isinstance(start_urls, list):
            raise TypeError, "Parameter 'start_urls' should be a list"

        self._thread_num = thread_num
        self.init_redis()
        self._push_to_queue(start_urls)
        self._open_log_file()

    
    def init_redis(self):
        try:
            self._queue = Queue('url', host=REDIS_HOST, port=int(REDIS_PORT))
        except ValueError, e:
            self._queue = Queue('url', host=REDIS_HOST, prot=6379)

    
    def _push_to_queue(self, urls):
        try:
            for url in urls:
                self._queue.append(url)
        except Exception, e:
            raise RedisQueueException, 'Failed to connect to redis server'

    
    def set_delay_logger(self, directory):
        self.__class__.delay_logger = open(directory, 'w')


    def set_error_logger(self, directory):
        self.__class__.error_logger = open(directory, 'w')


    def start(self):
        greenlets = []
        for idx in xrange(self._thread_num):
            greenlets.append(gevent.spawn(self._run, self))   

        gevent.joinall(greenlets)


    def _run(self):
        while True:
            if not _crawl():
                break;


    def _crawl(self):
        url = None
        for i in xrange(5):
            try:
                url = self._queue.pop()
            except Exception, e:
                gevent.sleep(2)
                continue
        if not url:
            return False
        # downloader should be multhreads


class CrawlerThread(Greenlet):

    def __init__(self):
        self._downloader = Downloader()
        self._urlextractor = UrlExtractor()
        # if 

    
    def _run(self):
        pass


class Downloader:
    '''
    Think about it. How to handle the problem when target site block us.
    So we need to simulate more like pepole behavior
    And we should do some log work when grab the web page
    '''
    
    def __init__(self, headers=None, domain=None):
        self._opener = urllib2.build_opener()
        self._opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0'),        
        ]
        self._delay_time = CrawlerEngine.DELAY_TIME
        self._delay_logger = CrawlerEngine.delay_logger
        self._error_logger = CrawlerEngine.error_logger
        self._404_re = re.compile(r'404：页面没有找到。')
        domain = domain if domain else 'm.sohu.com'
        self._domain_re = re.compile(r'http://(\w+\.)*%s' % domain)

    
    def set_domain(self, domain):
        self._domain_re = re.compile(r'http://(\w+\.)*%s' % domain)
        

    def set_404_re(self, character):
        '''
        Cause 404 page return 200 code on websit m.sohu.com,
        so I have to detect if it is a correct page.
        '''
        if not isinstance(character, str):
            raise ValueError, 'Parameter character should be str'
        self._404_re = re.compile(character)


    def get(self, url):
        '''
        Get a page specified by url
        Do logging works after downloading the page
        '''

        cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        starttime = time.time()
        try:
            resp = self._opener.open(url)
        except urllib2.HTTPError, resp:
            if self._domain_re.match(resp.url):
                self._error_logger.write('%s, %d, %s, %s,\n', (resp.url, \
                            resp.code, resp.msg, cur_time))
            return None
        except urllib2.socket.timeout, e:
            self._error_logger.write('%s,, %s, %s,\n', (url, \
                    'timeout', cur_time))
            return None

        # Cause the url we request may make a redirect
        # So we need check it out after
        if not self._domain_re.match(resp.url):
            return None

        if self._404_re.search(html):
            self._error_logger.write('%s, %d, %s, %s,\n', (resp.url, 404, \
                        '404 page which returns 200 code', cur_time))
            return None

        duration = time.time() - starttime
        if duration > self._delay_time:
            self._delay_logger.write('%s, %1.2f, %s,\n' % \
                        (resp.url, duration, cur_time))

        html = resp.read()
        return html


class UrlExtractor:
    '''
    UrlExtractor accept web page as input.
    It will parse the page and filter out all the
    undownloaded url then push them into the queue.
    '''

    def __init__(self, host=None, domain=None):
        self._anchor_re = re.compile(r'#')
        self._absolute_url_re = re.compile(r'http')
        self._host = host if host else 'http://m.sohu.com'
        domain = domain if domain else 'm.sohu.com'
        self._domain_re = re.compile(r'http://(\w+\.)*%s' % domain)


    def set_domain(self, domain):
        self._domain_re = re.compile(r'http://(\w+\.)*%s' % domain)


    def set_host(self, host):
        self._host = host


    def extract(self, html):
        '''
        Extract the urls from the given web page
        Return absoulte url, filter those don't belong to the specified domain
        Anchors are filtered as well
        '''

        url_eles = PyQuery(html)('a')
        urls = []
        for ele in url_eles:
            try:
                href = ele.attrib['href']
            except KeyError, e:
                continue
            if self._anchor_re.match(href):
                continue
            if not self._absolute_url_re.match(href):
                href = self._host + href
            if not self._domain_re.match(href):
                continue
            urls.append(href)
        return urls
