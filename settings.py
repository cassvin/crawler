# crawler settings
#

# Pages those are not belong to domain
# will not be crawled
DOMAIN = 'm.sohu.com'
SITE = 'http://m.sohu.com'

# Numbers of crawlers
CRAWLER_NUMBER = 2

# Url that spend more than $delaytime seconds will be logged
DELAY_TIME = 2

# Downloader will wait for $WAIT_TIME seconds 
# to continue next download
WAIT_TIME = 2

# Log files directory
ROOT_LOG = 'log'
DELAY_LOG = 'delay'
ERROR_LOG = 'error'

# I adopt redis as url queue
# Redis settings
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
