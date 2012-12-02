## Crawler

Crawler is what just as it's name, a web crawler, which you can give it some start urls and it will begin to work through the web site(you can specify in settings.py)

## Usage

Refer to the file [run] and [settings.py], you guys just type ./run and the crawler begin to work. If you need to do some custom settings, read settings.py and do some modifications. Keep settings.py empty is fine, cause 'crawler' will load default settings if variable not given.

## Done


## Todo


## Demand Description

(Sorry I use Chinese here, I will translate them to English sooner or later)

* 24小时不停的逛一个网站，如(http://m.sohu.com/)。

* 记录网站上出错的链接及出错链接的返回状态、内容等信息。

* 记录打开慢的网页，比如超过2秒。

* 分时段(小时，天)统计网站几个主要类型的网页打开的平均时间。

比如http://m.sohu.com 上的主要网页类型:

/n/xxx/ 新闻正文页 http://m.sohu.com/n/358627048/

/p/xxx/ 组图正文页 http://m.sohu.com/p/397297/

/c/xxx/ 频道首页 http://m.sohu.com/c/55/
