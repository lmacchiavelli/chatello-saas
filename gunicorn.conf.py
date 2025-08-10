import multiprocessing
import os

# Server socket
bind = "127.0.0.1:5010"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help limit memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '/var/www/flask/chatello-saas/logs/access.log'
errorlog = '/var/www/flask/chatello-saas/logs/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'chatello-saas'

# Server mechanics
daemon = False
pidfile = '/var/www/flask/chatello-saas/chatello-saas.pid'
user = 'www-data'
group = 'www-data'
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/etc/nginx/ssl/chatello.io.key'
# certfile = '/etc/nginx/ssl/chatello.io.crt'