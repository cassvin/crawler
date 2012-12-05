#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import urllib2
import httplib
import gevent
import gevent.coros
import time
import datetime
import redis
from pyquery import PyQuery
from redis_queue import Queue
from rediset import Rediset

try:
    urllib2.socket.setdefaulttimeout(TIMEOUT)
except Exception:
    urllib2.socket.setdefaulttimeout(15)

try:
    from settings import *
except ImportError:
    pass

if not 'DOMAIN' in globals():
    DOMAIN = 'm.sohu.com'
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
if not 'WAIT_TIME' in globals():
    WAIT_TIME = None


class RedisQueueException(Exception):
    pass


class LogFileException(Exception):
    pass


class CrawlerEngine:
    '''
    Core of the Crawler
    '''

    def __init__(self):
        try:
            self._delay_logger = open(os.path.join(ROOT_LOG, DELAY_LOG + '.log'), 'a')
            self._error_logger = open(os.path.join(ROOT_LOG, ERROR_LOG + '.log'), 'a')
        except IOError:
            raise LogFileException, 'Failed to open log file'

        self._redis_client = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
        self.downloaded_url = Rediset(hash_generated_keys=True,
                redis_client=self._redis_client).Set('downloaded_url_set')
        self.todownload_url_queue = Queue('todownload_url_queue',
                host=REDIS_HOST, port=REDIS_PORT)
        self.todownload_url_set = Rediset(hash_generated_keys=True,
                redis_client=self._redis_client).Set('todownload_url_set')

        self._rlock = gevent.coros.RLock()


    def __del__(self):
        pass

    def _push_to_queue(self, urls):
        try:
            for url in urls:
                self.todownload_url_queue.append(url)
                self.todownload_url_set.add(url)
        except redis.exceptions.ConnectionError:
            raise RedisQueueException, 'Failed to connect to redis server'

    def clear_data(self):
        try:
            self._redis_client.delete('downloaded_url_set', 'todownload_url_set',
                                      'todownload_url_queue')
        except redis.exceptions.ConnectionError:
            raise RedisQueueException, 'Failed to connect to redis server'

    def set_delay_logger(self, directory):
        self._delay_logger.close()
        self._delay_logger = open(directory, 'a')

    def set_error_logger(self, directory):
        self._error_logger.close()
        self._error_logger = open(directory, 'a')

    def clear_delay_logger(self, directory):
        pass

    def clear_error_logger(self, directory):
        pass

    def start(self, start_urls=None, contin=False):
        if start_urls is None:
            start_urls = []
        if not isinstance(start_urls, list):
            raise (TypeError, "Parameter 'start_urls' should be a list")
        if not contin:
            if len(start_urls) == 0:
                raise (Exception, 'You should specify at lease one start url')
            self.clear_data()
            self._push_to_queue(start_urls)
        greenlets = []
        for i in xrange(CRAWLER_NUMBER):
            greenlets.append(gevent.spawn(self._run))

        gevent.joinall(greenlets)

        print 'Hey buddy, I have finished my work.'

    def _run(self):
        downloader = Downloader(delay_logger=self._delay_logger,
                                error_logger=self._error_logger, domain=DOMAIN)
        urlextractor = UrlExtractor(domain=DOMAIN)

        while True:
            try:
                url = self.todownload_url_queue.popleft()
            except IndexError, e:
                gevent.sleep(5)
                try:
                    url = self.todownload_url_queue.popleft()
                except IndexError, e:
                    break

            self.todownload_url_set.remove(url)
            try:
                data = downloader.get(url)
            except Exception, e:
                print 'Uncaptured exception: (%s) arise when getting url: (%s), \
                        please check it out' % (e, url)
                continue
            finally:
                self.downloaded_url.add(url)

            if data is None:
                continue
            _url = data[0]
            html = data[1]
            # urlextractor.set_host(host)
            urls = urlextractor.extract(_url, html)
            self._rlock.acquire()
            urls = self._filter_undownloaded_urls(urls)
            self.todownload_url_queue.extend(urls)
            for url in urls:
                # cause the urls is too large, we need to add it one by one
                self.todownload_url_set.add(url)
            self._rlock.release()
            if not (WAIT_TIME is None):
                gevent.sleep(WAIT_TIME)

    def _filter_undownloaded_urls(self, urls):
        undownloaded_urls = []
        for url in urls:
            if (url in self.downloaded_url
                    or url in self.todownload_url_set):
                continue
            undownloaded_urls.append(url)
        return undownloaded_urls


class Downloader:
    '''
    Think about it. How to handle the problem when target site block us.
    So we need to simulate more like pepole behavior
    And we should do some log work when grab the web page
    '''

    def __init__(self, delay_logger=None, error_logger=None,
                 domain=None, headers=None):
        self._opener = urllib2.build_opener()
        self._opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0'),
        ]
        self._delay_time = DELAY_TIME
        self._delay_logger = delay_logger
        self._error_logger = error_logger
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

        print url
        cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        starttime = time.time()
        try:
            resp = self._opener.open(url)
        except urllib2.HTTPError, resp:
            if self._domain_re.match(resp.url):
                if self._error_logger:
                    self._error_logger.write('%s, %d, %s, %s,\n' % (resp.url,
                                             resp.code, resp.msg, cur_time))
            return None
        except urllib2.URLError, e:
            if self._error_logger:
                self._error_logger.write('%s,, %s, %s,\n' % (url,
                                         e.reason.strerror, cur_time))
            return None
        except httplib.InvalidURL, e:
            if self._error_logger:
                self._error_logger.write('%s,,%s, %s,\n' % (url,
                                         e.message, cur_time))
            return None
        except urllib2.socket.timeout, e:
            if self._error_logger:
                self._error_logger.write('%s,, %s, %s,\n' % (url,
                                         e.message, cur_time))
            return None

        duration = time.time() - starttime

        # Cause the url we request may make a redirect
        # So we need check it out after
        if self._domain_re:
            if not self._domain_re.match(resp.url):
                return None

        html = resp.read()
        if self._404_re.search(html):
            if self._error_logger:
                self._error_logger.write('%s, %d, %s, %s,\n' % (resp.url, 404,
                                         '404 page which returns 200 code', cur_time))
            return None

        if duration > self._delay_time:
            if self._delay_logger:
                self._delay_logger.write('%s, %1.2f, %s,\n' %
                                         (resp.url, duration, cur_time))

        # cause we have check the url before, we neen't
        # to do forward check but just get it's value
        return (resp.url, html)

    def get_download_time(self, url):
        starttime = time.time()
        try:
            self._opener.open(url)
        except Exception:
            return None

        duration = time.time() - starttime
        return duration


class UrlExtractor:
    '''
    UrlExtractor accept web page as input.
    It will parse the page and filter out all the
    undownloaded url then push them into the queue.
    '''

    def __init__(self, domain=None):
        self._anchor_re = re.compile(r'#')
        self._absolute_url_re = re.compile(r'http')
        self._email_re = re.compile(r'mailto:')
        self._js_re = re.compile(r'javascript:')
        domain = domain if domain else 'm.sohu.com'
        self._domain_re = re.compile(r'http://(\w+\.)*%s' % domain)
        self._prefix_re = re.compile(r'/')
        self._relative_url_re = re.compile(r'/\.\.')
        self._parent_dir_re = re.compile(r'http://(\w+\.)*%s/(\w+)/' % domain)

    def set_domain(self, domain):
        self._domain_re = re.compile(r'http://(\w+\.)*%s' % domain)

    def set_host(self, host):
        self._host = host

    def extract(self, url, html):
        '''
        Extract the urls from the given web page
        Return absoulte url, filter those don't belong to the specified domain
        Anchors are filtered as well
        '''

        host = self._domain_re.match(url).group(0)
        if not host:
            host = 'http://m.sohu.com'
        url_eles = PyQuery(html)('a')
        urls = {}
        for ele in url_eles:
            try:
                href = ele.attrib['href']
            except KeyError:
                continue
            if self._anchor_re.match(href):
                continue
            if self._email_re.match(href):
                continue
            if self._js_re.match(href):
                continue
            if not self._absolute_url_re.match(href):
                if not self._prefix_re.match(href):
                    href = '/' + href
                if self._relative_url_re.match(href):
                    try:
                        parent_dir = self._parent_dir_re.match(url).groups(0)[1]
                        href = href[:3].replace('..', parent_dir) + href[3:]
                    except Exception:
                        pass
                href = host + href
            if not self._domain_re.match(href):
                continue
            urls[href] = 1
        return urls.keys()
