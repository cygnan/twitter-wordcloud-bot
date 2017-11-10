#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import sys
import time
import urllib
import tweepy
from wordcloud import WordCloud
from natto import MeCab

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logging.basicConfig(format='[%(filename)s:%(lineno)d] %(message)s')
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

      LOGGER.info('@%s: "%s"', tweet_username, tweet_text)


      is_retweet = "RT " in tweet_text
      if is_retweet:
        LOGGER.info("-> Skipped (is_retweet).")
      else:
        is_not_reply = status.in_reply_to_screen_name is None or "@" not in tweet_text or " " not in tweet_text
        if is_not_reply:
          LOGGER.info("-> Skipped (is_not_reply).")
        else:
          tweet_to = str(status.in_reply_to_screen_name)
          tweet_id = status.id

          is_not_reply_to_me = tweet_to != MY_TWITTER_USERNAME
          if is_not_reply_to_me:
            LOGGER.info("-> Skipped (is_not_reply_to_me).")
          else:
            try:
              query = tweet_text.split(" ", tweet_text.count("@"))[-1]
              query_encoded = urllib.quote_plus(query)

              from collections import defaultdict
              frequency = defaultdict(int)

              MAX_TWEETS = 1000

              while True:
                try:
                  LOGGER.info('Searching "%s"...', query)
                  searched_tweets = [status for status in tweepy.Cursor(
                      api.search, q=query_encoded).items(MAX_TWEETS)]
                  break
                except Exception as e:
                  is_429_too_many_requests_error = str(e).find("429") != -1
                  if is_429_too_many_requests_error:
                    LOGGER.warning("429 Too Many Requests. Waiting 1 minute...")
                    time.sleep(60)
                  else:
                    raise Exception("[line {0}] {1}".format(sys.exc_info()[-1].tb_lineno, e))
              
              LOGGER.info('-> %s tweets were found.', str(len(searched_tweets)))

              no_hit = len(searched_tweets) == 0
              if no_hit:
                my_reply = "@{0} Your search - {1} - did not match any tweets. Try different keywords.".format(tweet_username, query)

                api.update_status(status=my_reply, in_reply_to_status_id=tweet_id)

                LOGGER.info('-> Tweeted "%s"', my_reply)
              else:
                stop_words = ['てる', 'いる', 'なる', 'れる', 'する', 'ある',
                              'こと', 'これ', 'さん', 'して', 'くれる', 'やる',
                              'くださる', 'そう', 'せる', 'した',  '思う', 'それ',
                              'ここ', 'ちゃん', 'くん', '', 'て', 'に', 'を',
                              'は', 'の', 'が', 'と', 'た', 'し', 'で', 'ない',
                              'も', 'な', 'い', 'か', 'ので', 'よう', '', 'RT',
                              '@', 'http', 'https', '.', ':', '/', '//', '://']

                with MeCab() as nm:
                  for node in nm.parse(query, as_nodes=True):
                    word = node.surface
                    stop_words.append(word)

                LOGGER.info("Doing morphological analysis using MeCab...")

                for tweet in searched_tweets:
                  text = str(tweet.text.encode("utf-8"))
                  # filter(tweet.text.encode("utf-8"))

                  with MeCab() as nm:
                    for node in nm.parse(text, as_nodes=True):
                      word = node.surface

                      is_not_stop_word = word not in stop_words
                      if is_not_stop_word:
                        word_type = node.feature.split(",")[0]
                        word_decoded = word.decode('utf-8')
                        if word_type == "形容詞":
                          if word_decoded[-1:] == "く":
                            frequency[word_decoded] += 1
                          else:
                            frequency[word_decoded] += 100
                        elif word_type in ["動詞", "名詞", "副詞"]:
                          frequency[word_decoded] += 1

                LOGGER.info("-> Done.")

                font_path = "GenShinGothic-P-Medium.ttf"

                wordcloud = WordCloud(background_color="white", width=900,
                                      height=450, font_path=font_path)

                LOGGER.info("Generating a wordcloud image...")

                wordcloud_image = wordcloud.generate_from_frequencies(
                    frequencies=frequency)

                file_path = "/tmp/{0}.png".format(str(tweet_id))
                wordcloud_image.to_file(file_path)
                LOGGER.info('-> Saved a wordcloud image to "%s"',file_path)

                my_reply = '@{0} Search results for "{1}" (about {2} tweets)'.format(
                    tweet_username, query, str(len(searched_tweets)))  # Test

                api.update_with_media(filename=file_path, status=my_reply,
                                      in_reply_to_status_id=tweet_id)

                LOGGER.info('Tweeted "%s"', my_reply)
            except Exception as e:
              LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)

              my_reply = "500 Internal Server Error. Sorry, something went wrong."

              api.update_status(
                  status=my_reply, in_reply_to_status_id=tweet_id)

              LOGGER.info('Tweeted "%s"', my_reply)
      return

    except Exception as e:
      LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)

  def on_error(self, status_code):
    LOGGER.warning("Error")
    LOGGER.error(status_code)


def certify():
  auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
  auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
  api = tweepy.API(auth)
  return api


if IS_TRAVIS_CI is True:
  LOGGER.info("Started Travis CI building test...")

api = certify()

LOGGER.info("Authentication successful.")

MY_TWITTER_USERNAME = str(api.me().screen_name)
LOGGER.info("Hello @%s!",MY_TWITTER_USERNAME)

if IS_TRAVIS_CI is True:
  sys.exit()

try:
  MY_STREAM = tweepy.Stream(auth=api.auth, listener=MyStreamListener())

  LOGGER.info("Started streaming...")

  MY_STREAM.userstream()

  LOGGER.info("Finished streaming.")

except Exception as e:
  LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)
