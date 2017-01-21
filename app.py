# -*- coding: utf-8 -*-
import json
import os
import urllib.parse
from functools import wraps

import bottle
from bottle import (
    route,
    run,
    jinja2_template as template,
    redirect,
    request,
    response,
    static_file,
    BaseTemplate,
)
import tweepy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
BaseTemplate.settings.update(
    {
        'filters': {
            'encode_query': lambda query: urllib.parse.urlencode({'q': query})
        }
    }
)


#######################################################################################################################
#
# Middleware
#
#######################################################################################################################
class TwitterManager(object):
    def __init__(self, consumer_key, consumer_secret, access_token=None,
                 access_token_secret=None, callback_url=None):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.callback_url = callback_url
        self.request_token = None
        self.api = None

    def get_authorization_url(self):
        auth = tweepy.OAuthHandler(self.consumer_key,
                                   self.consumer_secret,
                                   self.callback_url)
        try:
            redirect_url = auth.get_authorization_url()
        except tweepy.TweepError:
            raise tweepy.TweepError('Error! Failed to get request token')
        self.request_token = auth.request_token
        return redirect_url

    def get_access_token(self, verifier):
        auth = tweepy.OAuthHandler(self.consumer_key,
                                   self.consumer_secret)
        if self.request_token is None:
            raise tweepy.TweepError("Request token not set yet.")
        auth.request_token = self.request_token
        try:
            auth.get_access_token(verifier)
        except tweepy.TweepError:
            raise tweepy.TweepError('Error! Failed to get access token')
        return (
            auth.access_token,
            auth.access_token_secret,
        )

    def set_access_token(self, key, secret):
        self.access_token = key
        self.access_token_secret = secret

    def get_oauth_api(self, access_token, access_token_secret):
        auth = tweepy.OAuthHandler(self.consumer_key,
                                   self.consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        return tweepy.API(auth)

    def set_api(self):
        self.api = self.get_oauth_api(self.access_token, self.access_token_secret)

    def authenticate(self, verifier):
        token = self.get_access_token(verifier)
        self.set_access_token(*token)
        self.set_api()


class TwitterMiddleware(object):

    def __init__(self, app, tweepy_config):
        self.app = app
        self.tweepy_settings = tweepy_config
        self.tweepy_manager = TwitterManager(**self.tweepy_settings)

    def __call__(self, environ, start_response):
        environ['twitter'] = self.tweepy_manager
        return self.app(environ, start_response)


#######################################################################################################################
#
# Decorators
#
#######################################################################################################################
def login_required(f):
    @wraps(f)
    def _login_required(*args, **kwargs):
        twitter = request.environ.get('twitter')
        if twitter.api is None:
            return redirect('/')
        return f(*args, **kwargs)
    return _login_required


#######################################################################################################################
#
# Controllers
#
#######################################################################################################################
@route('/static/<filename:path>')
def send_static(filename):
    return static_file(filename, root=STATIC_DIR)


@route('/')
def index():
    return template('index')


@route('/oauth')
def oauth():
    twitter = request.environ.get('twitter')
    redirect_url = twitter.get_authorization_url()
    return redirect(redirect_url)


@route('/verify')
def verify():
    twitter = request.environ.get('twitter')
    verifier = request.params.get('oauth_verifier')
    twitter.authenticate(verifier)
    return redirect('home')


@route('/home')
@login_required
def home():
    twitter = request.environ.get('twitter')
    user = twitter.api.me()
    return template('home', user=user)


@route('/api/saved_searches/list')
@login_required
def get_saved_searches():
    twitter = request.environ.get('twitter')
    saved_searches = twitter.api.saved_searches()
    data = []
    for s in saved_searches:
        timestamp = s.created_at.strftime('%Y-%m-%d %H:%M:%S')
        data.append({'id': s.id, 'name': s.name, 'query': s.query, 'timestamp': timestamp})

    response.headers['Content-Type'] = 'application/json'
    return json.dumps(data)


if __name__ == "__main__":
    twitter_config = {
        'consumer_key': os.environ['TSSM_CONSUMER_KEY'],
        'consumer_secret': os.environ['TSSM_CONSUMER_SECRET'],
        'callback_url': 'http://127.0.0.1:8000/verify',
    }
    app = TwitterMiddleware(bottle.app(), twitter_config)
    run(app=app, host="localhost", port=8000, debug=True, reloader=True)
