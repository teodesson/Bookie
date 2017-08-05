set BOOKIE_INI=test.ini
celery worker --app=bookie.bcelery -l debug --pidfile celeryd.pid &