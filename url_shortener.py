"""
  Url Shortener
"""
from __future__ import with_statement
import json, re
from sqlite3 import dbapi2 as sqlite3
from contextlib import closing
from flask import jsonify, Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

# configuration
DATABASE = '/tmp/url_shortener.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('URL_SHORTENER_SETTINGS', silent=True)


def _create_url(uid):
    """
    Short hash function which takes an integer id and shortens it using a base
    62 counting hash (based on implementation from http://code.google.com/p/urly/)
    """
    HASH_BASE = 'lahcx9yV6OsuefCEvJAbd0SZIGWYFQtUB8KX5jqR4NMzH1PTg37npwrLimD2ko'
    s = []
    mod = len(HASH_BASE)
    while uid:
        uid, c = divmod(uid, mod)
        s.append(HASH_BASE[c])
    return ''.join(s)

def _get_short_url(shash):
    # TODO: implement cache
    cur = g.db.execute('select id, url from urls where short = ?', [shash])
    row = cur.fetchone()
    return (row[0], row[1]) if row else (None, None)

@app.route('/')
def show_urls():
    # TODO: paginate
    cur = g.db.execute('select id, url, short from urls order by id desc')
    urls = [dict(id=row[0], url=row[1], short=row[2]) for row in cur.fetchall()]
    return render_template('show_urls.html', urls=urls)

@app.route('/shorten_url', methods=['POST'])
def add_url():
    if request.method == 'POST':
      data = None
      # Handle mimetype 'application/json' or other
      if request.json:
        data = request.json
      else:
        if not request.data:
          return jsonify(success=False, message='Please provide `long_url` parameter in json format.')

        try:
          data = json.loads(request.data)
        except ValueError, ex:
          return jsonify(success=False, message='Could not parse json.')

      if not data or not data['long_url']:
        return jsonify(success=False, message='Required parameter "long_url" missing.')

      long_url, custom_url = data.get('long_url'), data.get('custom_short_code')
      if custom_url:
        id, url = _get_short_url(custom_url)
        if url:
          return jsonify(success=False, message='Custom URL already taken.')
        elif re.match(r'[^0-9a-zA-Z]', custom_url):
          return jsonify(success=False, message='Only alphanumeric characters are supported for custom urls.')


      if custom_url:
        g.db.execute('insert into urls (url, short) values (?, ?)', [long_url, custom_url])
      else:
        g.db.execute('insert into urls (url) values (?)', [data['long_url']])
        id = g.db.execute('select last_insert_rowid();').fetchone()[0]
        short = _create_url(id)
        id = g.db.execute('update urls set short = ? where id = ?', [short, id])
      g.db.commit()

      return jsonify(success=True, short_url=custom_url or short)
    return redirect(url_for('show_urls'))

@app.route('/<shash>')
def follow(shash):
    id, url = _get_short_url(shash)
    if not url:
      response = jsonify(success=False, message='Url not found', code=404)
      response.status_code = 404
      return response
    g.db.execute('update urls set count=count+1 where id = %i' % id)
    return redirect(url)

'''
  Utilities
'''

def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    """Make sure we are connected to the database each request."""
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

if __name__ == '__main__':
    app.run()
