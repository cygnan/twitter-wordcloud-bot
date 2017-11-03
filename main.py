#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import tweepy

logging.basicConfig()
log = logging.getLogger("main.py")
log.setLevel(logging.DEBUG)

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
            tweetUserName = str(status.user.screen_name)
            tweetTo = str(status.in_reply_to_screen_name)
            tweetText = str(status.text.encode('utf_8'))

            log.info("@{}: \"{}\"".format(tweetTo, tweetText))

            if tweetTo == str(api.me().screen_name):
                reply = "@" + tweetUserName + " " + tweetText #Test

                api.update_status(status=reply)

                log.info("-> Tweeted \"{}\"".format(reply))
            else:
                log.info("-> Skipped.")
            return

        except Exception as e:
            log.warning(e)

    def on_error(self, status_code):
        log.warning("Error")
        log.error(status_code)

try:
    print("Hello @{}!".format(api.me().screen_name))

    myStreamListener = MyStreamListener()
    myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)

    log.info("Started streaming...")

    myStream.userstream()

    log.info("Finished streaming.")

except Exception as e:
    log.warning(e)
