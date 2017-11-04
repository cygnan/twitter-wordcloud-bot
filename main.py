#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import tweepy

logging.basicConfig()
logger = logging.getLogger("main.py")
logger.setLevel(logging.DEBUG)

CONSUMER_KEY = os.environ["CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        try:
            tweet_username = str(status.user.screen_name)
            tweet_to = str(status.in_reply_to_screen_name)
            tweet_text = str(status.text.encode('utf_8'))

            logger.info('@{}: "{}"'.format(tweet_to, tweet_text))

            if tweet_to == str(api.me().screen_name):
                my_reply = "@" + tweet_username + " " + tweet_text #Test

                api.update_status(status=my_reply)

                logger.info('-> Tweeted "{}"'.format(my_reply))
            else:
                logger.info("-> Skipped.")
            return

        except Exception as e:
            logger.warning(e)

    def on_error(self, status_code):
        logger.warning("Error")
        logger.error(status_code)

try:
    print("Hello @{}!".format(api.me().screen_name))

    my_stream_listener = MyStreamListener()
    my_stream = tweepy.Stream(auth=api.auth, listener=my_stream_listener)

    logger.info("Started streaming...")

    my_stream.userstream()

    logger.info("Finished streaming.")

except Exception as e:
    logger.warning(e)
