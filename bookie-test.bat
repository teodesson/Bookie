echo off
set NLTK_DATA=.\download-cache\ntlk
set INI=test.ini

echo py.test -q --tb=short -s bookie/tests > result.txt
echo py.test -q --tb=short -s bookie/tests/test_api > result.txt
nosetests bookie.tests.test_api > result.txt 2>&1
