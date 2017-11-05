#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import sys
import tweepy

logging.basicConfig()
LOGGER = logging.getLogger("main.py")
LOGGER.setLevel(logging.DEBUG)

CONSUMER_KEY = os.environ["CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]

if len(sys.argv) == 2 and str(sys.argv[1]) == "--travis":
    IS_TRAVIS_CI = True
else:
    IS_TRAVIS_CI = False


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        try:
            tweet_username = str(status.user.screen_name)
            tweet_text = str(status.text.encode('utf_8'))

            LOGGER.info('@{0}: "{1}"'.format(tweet_username, tweet_text))

            if status.in_reply_to_screen_name is None:
                LOGGER.info("-> Skipped.")
            else:
                tweet_to = str(status.in_reply_to_screen_name)

                if tweet_to != MY_TWITTER_USERNAME:
                    LOGGER.info("-> Skipped.")
                else:
                    my_reply = "@" + tweet_username + " " + tweet_text  # Test

                    API.update_status(status=my_reply)

                    LOGGER.info('-> Tweeted "{0}"'.format(my_reply))

            return

        except Exception as e:
            LOGGER.warning(e)

    def on_error(self, status_code):
        LOGGER.warning("Error")
        LOGGER.error(status_code)


if IS_TRAVIS_CI is True:
    LOGGER.info("Started Travis CI building test...")

AUTH = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
AUTH.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
API = tweepy.API(AUTH)

LOGGER.info("Authentication successful.")

MY_TWITTER_USERNAME = str(API.me().screen_name)
LOGGER.info("Hello @{0}!".format(MY_TWITTER_USERNAME))

if IS_TRAVIS_CI is True:
    sys.exit()

try:
    MY_STREAM = tweepy.Stream(auth=API.auth, listener=MyStreamListener())

    LOGGER.info("Started streaming...")

    MY_STREAM.userstream()

    LOGGER.info("Finished streaming.")

except Exception as e:
    LOGGER.warning(e)
