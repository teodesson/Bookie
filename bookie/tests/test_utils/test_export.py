"""Tests that we make sure our export functions work"""
import json
import logging
import random

from urllib.parse import urlencode

from bookie.tests import TestViewBase


LOG = logging.getLogger(__name__)
API_KEY = None


class TestExport(TestViewBase):
    """Test the web export"""

    def _get_good_request(self, is_private=False, url=None, dt=None):
        """Return the basics for a good add bookmark request"""
        if not url:
            url = 'http://google.com'

        prms = {
            'url': url,
            'description': 'This is my google desc',
            'extended': 'And some extended notes about it in full form',
            'tags': 'python search',
            'is_private': is_private,
            'dt': dt
        }

        res = self.app.post(
            '/api/v1/admin/bmark?api_key={0}'.format(self.api_key),
            content_type='application/json',
            params=json.dumps(prms),
        )
        return res

    def _get_good_request_wo_tags(self):
        """Return the basics for a good add bookmark request
            without any tags"""
        prms = {
            'url': 'http://bmark.us',
            'description': 'This is my bmark desc',
            'extended': 'And some extended notes about it in full form',
            'tags': '',
        }

        req_params = urlencode(prms)
        res = self.app.post(
            '/api/v1/admin/bmark?api_key={0}'.format(self.api_key),
            params=req_params,
        )
        return res

    def _get_random_date(self):
        """Returns a random date in ISO 8061 - "%Y-%m-%dT%H:%M:%SZ" format"""
        iso_format = "{year}-{month}-{day}T{hour}:{minute}:{second}Z"
        year_range = [str(i) for i in range(1900, 2014)]
        month_range = [str(i).zfill(2) for i in range(1, 13)]
        day_range = [str(i).zfill(2) for i in range(1, 28)]
        hour_range = [str(i).zfill(2) for i in range(1, 25)]
        min_range = [str(i).zfill(2) for i in range(1, 60)]

        args = {
            "year": random.choice(year_range),
            "month": random.choice(month_range),
            "day": random.choice(day_range),
            "hour": random.choice(hour_range),
            "minute": random.choice(min_range),
            "second": random.choice(min_range)
        }

        return iso_format.format(**args)

    def test_export(self):
        """Test that we can upload/import our test file"""
        self._get_good_request()

        self._login_admin()
        res = self.app.get(
            '/api/v1/admin/bmarks/export?api_key={0}'.format(
                self.api_key),
            status=200)

        self.assertTrue(
            "google.com" in res.unicode_body,
            msg='Google is in the exported body: ' + res.unicode_body)
        data = json.loads(res.unicode_body)

        self.assertEqual(
            1,
            data['count'],
            "Should be one result: " + str(data['count']))

    def test_export_wo_tags(self):
        """Test that we can upload/import our test file"""
        self._get_good_request_wo_tags()

        self._login_admin()
        res = self.app.get(
            '/api/v1/admin/bmarks/export?api_key={0}'.format(
                self.api_key),
            status=200)

        self.assertTrue(
            "bmark.us" in res.unicode_body,
            msg='Bmark is in the exported body: ' + res.unicode_body)
        data = json.loads(res.unicode_body)

        self.assertEqual(
            1,
            data['count'],
            "Should be one result: " + str(data['count']))

    def test_export_view(self):
        """Test that we get IS_PRIVATE attribute for each bookmark during
        export"""
        self._get_good_request()

        self._login_admin()
        res = self.app.get('/admin/export?api_key=' + self.api_key, status=200)

        self.assertTrue(
            "google.com" in res.unicode_body,
            msg='Google is in the exported body: ' + res.unicode_body)

        self.assertTrue(
            'PRIVATE="1"' not in res.unicode_body,
            "Bookmark should be a public bookmark: " + res.unicode_body)

    def test_export_view_accounts_for_privacy(self):
        """Test that we get IS_PRIVATE attribute for each bookmark during
        export"""
        self._get_good_request(is_private=True)
        self._login_admin()
        res = self.app.get('/admin/export?api_key=' + self.api_key, status=200)

        self.assertTrue(
            "google.com" in res.unicode_body,
            msg='Google is in the exported body: ' + res.unicode_body)

        self.assertTrue(
            'PRIVATE="1"' in res.unicode_body,
            "Bookmark should be a private bookmark: " + res.unicode_body)

    def test_export_view_is_sorted(self):
        """Test that we get bookmarks sorted by 'stored' attribute during
        export"""
        self._get_good_request(url='https://google.com',
                               dt=self._get_random_date())
        self._get_good_request(url='https://twitter.com',
                               dt=self._get_random_date())
        self._get_good_request(url='https://github.com',
                               dt=self._get_random_date())

        res = self.app.get(
            '/api/v1/admin/bmarks/export?api_key={0}'.format(
                self.api_key),
            status=200)

        data = json.loads(res.unicode_body)

        self.assertEqual(
            3,
            data['count'],
            msg="Should be three results: " + str(data['count']))

        res_bmarks = data['bmarks']
        sorted_bmarks = sorted(res_bmarks,
                               key=lambda k: k['stored'],
                               reverse=True)

        self.assertEqual(
            res_bmarks,
            sorted_bmarks,
            msg="Bookmarks should be sorted in descending order"
        )
