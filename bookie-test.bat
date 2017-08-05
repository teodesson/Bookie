echo off
set NLTK_DATA=.\download-cache\ntlk
set INI=test.ini

echo py.test -q --tb=short -s bookie/tests/test_api > result.txt
py.test -q --tb=short -s bookie/tests > result.txt
