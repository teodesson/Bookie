set BOOKIE_INI=bookie.ini
celery worker --app=bookie.bcelery -l debug --pidfile celeryd.pid &