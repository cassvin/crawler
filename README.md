## Crawler

Crawler is what just as it's name, a web crawler, which you can give it some start urls and it will begin to work through the web site(you can specify in settings.py)

## Usage

Refer to the file [run] and [settings.py], you guys just type ./run and the crawler begin to work. If you need to do some custom settings, read settings.py and do some modifications. Keep settings.py empty is fine, cause 'crawler' will load default settings if variable not given.

The script statistic visit different kinds of web links specified in 'links/\*'(by default, actually you can specified it in settings.py, and I have prepared some links in this default directory) and record how much time each kind of links cost to visit. And then these statistic data will be recorded in 'statistic\_data/\*'(by default as well). What you need to do is create you own crontab job to make sure this script run every interval you want, just as like below:

* 0 \*/1 \* \* \*          /home/cassvin/Project/Python/crawler/statistic
* 30 12 \*/1 \* \*        /home/cassvin/Project/Python/crawler/statistic

## Dependence

  Python lib:

      * redis_queue
      * rediset
      * PyQuery
      * gevent

  Software:
      
      * redis


## Demand Description

(Chinese here, I will translate them into English sooner or later)

* 24小时不停的逛一个网站，如(http://m.sohu.com/)。

* 记录网站上出错的链接及出错链接的返回状态、内容等信息。

* 记录打开慢的网页，比如超过2秒。

* 分时段(小时，天)统计网站几个主要类型的网页打开的平均时间。

比如http://m.sohu.com 上的主要网页类型:

/n/xxx/ 新闻正文页 http://m.sohu.com/n/358627048/

/p/xxx/ 组图正文页 http://m.sohu.com/p/397297/

/c/xxx/ 频道首页 http://m.sohu.com/c/55/

