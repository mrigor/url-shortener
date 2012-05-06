"""
    Tests
"""
import os
import json
import unittest
import tempfile

import url_shortener as shortener


class ShortenerTestCase(unittest.TestCase):

    def setUp(self):
        """Before each test, set up a blank database"""
        self.db_fd, shortener.app.config['DATABASE'] = tempfile.mkstemp()
        shortener.app.config['TESTING'] = True
        self.app = shortener.app.test_client()
        shortener.init_db()

    def tearDown(self):
        """Get rid of the database again after each test."""
        os.close(self.db_fd)
        os.unlink(shortener.app.config['DATABASE'])

    # testing functions

    def test_empty_db(self):
        """Start with a blank database."""
        rv = self.app.get('/')
        assert 'No urls here so far' in rv.data

    def test_missing_params(self):
        rv = self.app.post('/shorten_url',
            data='')
        data = json.loads(rv.data)
        assert data['success'] == False
        assert data['message'] == 'Please provide `long_url` parameter in json format.'

    def test_bad_json(self):
        rv = self.app.post('/shorten_url',
            data='{-}')
        data = json.loads(rv.data)
        assert data['success'] == False
        assert data['message'] == 'Could not parse json.'

    def test_url_creation(self):
        """Test that urls are created"""
        rv = self.app.post('/shorten_url',
            data='{"long_url":"http://google.com/"}',
            follow_redirects=True)
        data = json.loads(rv.data)
        assert 'success' in data
        assert data['success'] == True
        assert 'short_url' in data
        # Test redirect
        rv = self.app.get('/%s' % data['short_url'], follow_redirects=False)
        assert rv.status_code == 302
        assert rv.location == 'http://google.com/'

    def test_custom_url_alphanum_support(self):
        rv = self.app.post('/shorten_url',
            data='{"custom_short_code":"-", "long_url":"a"}',
            follow_redirects=True)
        data = json.loads(rv.data)
        assert data['success'] == False
        assert data['message'] == 'Only alphanumeric characters are supported for custom urls.'

    def test_custom_url_collision(self):
        rv = self.app.post('/shorten_url',
            data='{"custom_short_code":"abcdef", "long_url":"http://google.com/"}',
            follow_redirects=True)
        data = json.loads(rv.data)
        assert data['short_url'] == 'abcdef'

        #collision
        rv = self.app.post('/shorten_url',
            data='{"custom_short_code":"abcdef", "long_url":"http://google.com/"}',
            follow_redirects=True)
        data = json.loads(rv.data)
        assert data['success'] == False
        assert data['message'] == 'Custom URL already taken.'


    def test_redirection(self):
        rv = self.app.post('/shorten_url',
            data='{"long_url":"http://test.com"}')
        short = json.loads(rv.data)['short_url']
        rv = self.app.get('/%s' % short,
            follow_redirects=False)
        assert 'Location: http://test.com' in str(rv.headers)
        assert rv.status_code == 302


if __name__ == '__main__':
    unittest.main()
