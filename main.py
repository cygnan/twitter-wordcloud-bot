#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import time
import urllib
from collections import defaultdict

import matplotlib
import tweepy
from natto import MeCab
from wordcloud import WordCloud

matplotlib.use('Agg')  # Set the filetype	to png

logging.basicConfig(format='[%(filename)s:%(lineno)d] %(message)s')
LOGGER = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
LOGGER.setLevel(logging.DEBUG)

IS_TRAVIS_CI = bool(len(sys.argv) == 2 and str(sys.argv[1]) == "--travis")

if not IS_TRAVIS_CI:
  CONSUMER_KEY = os.environ["CONSUMER_KEY"]
  CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
  ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
  ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]


class MyStreamListener(tweepy.StreamListener):
  def on_status(self, status):
    if is_mention_or_reply_to_me(status):
      try:
        tweet_username = str(status.user.screen_name)
        tweet_text = str(status.text.encode('utf_8'))
        tweet_id = status.id

        query = tweet_text.split(" ", tweet_text.count("@"))[-1]
        query_encoded = urllib.quote_plus(query)

        frequency = defaultdict(int)

        MAX_TWEETS = 500

        while True:
          try:
            LOGGER.info('Searching "%s"...', query)
            searched_tweets = [status for status in tweepy.Cursor(
                api.search, q=query_encoded, lang="ja").items(MAX_TWEETS)]
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

          res = reply(api=api, in_reply_to_status_id=tweet_id, status=my_reply)
          if res == "Error":
            raise Exception("Failed to tweet.")

        else:
          stop_words = ['てる', 'いる', 'なる', 'れる', 'する', 'ある',
                        'こと', 'これ', 'さん', 'して', 'くれる', 'やる',
                        'くださる', 'そう', 'せる', 'した', '思う', 'それ',
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

            with MeCab() as nm:
              for node in nm.parse(text, as_nodes=True):
                word = node.surface

                is_not_stop_word = word not in stop_words
                if is_not_stop_word:
                  word_type = node.feature.split(",")[0]
                  word_decoded = node.surface.decode('utf-8')
                  word_original_form_decoded = node.feature.split(
                    ",")[6].decode('utf-8')
                  if word_type == "形容詞":
                    frequency[word_original_form_decoded] += 100
                  elif word_type == "動詞":
                    frequency[word_original_form_decoded] += 1
                  elif word_type in ["名詞", "副詞"]:
                    frequency[word_decoded] += 1

          LOGGER.info("-> Done.")

          font_path = "rounded-mplus-1p-bold.ttf"

          wordcloud = WordCloud(background_color="white", width=900,
                                height=450, font_path=font_path,
                                min_font_size=12)

          LOGGER.info("Generating a wordcloud image...")

          wordcloud_image = wordcloud.generate_from_frequencies(
              frequencies=frequency)

          file_path = "/tmp/{0}.png".format(str(tweet_id))
          wordcloud_image.to_file(file_path)
          LOGGER.info('-> Saved a wordcloud image to "%s"', file_path)

          my_reply = '@{0} Search results for "{1}" (about {2} tweets)'.format(
              tweet_username, query, str(len(searched_tweets)))  # Test

          res = reply(api=api, in_reply_to_status_id=tweet_id, status=my_reply,
                      filename=file_path)
          if res == "Error":
            raise Exception("Failed to tweet.")

      except Exception as e:
        LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)

        my_reply = "@{0} 500 Internal Server Error. Sorry, something went wrong.".format(tweet_username)

        res = reply(api=api, in_reply_to_status_id=tweet_id,
                    status=my_reply)
        if res == "Error":
          raise Exception("Failed to tweet.")

    return

  def on_error(self, status_code):
    LOGGER.warning("Error")
    LOGGER.error(status_code)


def certify():
  """
  Authenticate with Twitter using Tweepy and return Twitter API object.

  :returns: Twitter API object
  :rtype: Twitter API object
  """
  auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
  auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
  api = tweepy.API(auth)
  return api


def is_mention_or_reply_to_me(status):
  """
  Determine whether the tweet is a mention or a reply to me or not.

  :param status: A tweet status
  :type status: A tweet object
  :returns: True if the tweet is a mention or a reply to me, otherwise False
  :rtype: bool
  """
  try:
    tweet_username = str(status.user.screen_name)
    tweet_text = str(status.text.encode('utf_8'))

    LOGGER.info('@%s: "%s"', tweet_username, tweet_text)

    # If the tweet is a retweet, then skipped.
    if "RT " in tweet_text:
      LOGGER.info("-> Skipped (a retweet).")
      return False

    # If the tweet is neither a mention nor a reply, then skipped.
    if status.in_reply_to_screen_name is None or "@" not in tweet_text or " " not in tweet_text:
      LOGGER.info("-> Skipped (neither a mention nor a reply).")
      return False

    tweet_to = str(status.in_reply_to_screen_name)
    tweet_id = status.id

    # If the tweet is neither a mention nor a reply to me, then skipped.
    if tweet_to != MY_TWITTER_USERNAME:
      LOGGER.info("-> Skipped (neither a mention nor a reply to me).")
      return False

    return True

  except Exception as e:
    LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)


def reply(api, in_reply_to_status_id, status=None, filename=None):
  """
  Reply with either text, an image, or both

  :param api: Twitter API object (required)
  :type api: Twitter API object
  :param int in_reply_to_status_id: The ID of an existing status that the update is in reply to (required)
  :param str status: The text of your status update (optional)
  :param str filename: The local path to image file to upload (optional)
  :returns: "Error" if something goes wrong, otherwise None
  :rtype: str or None

  :Example:

  >>> reply(api=api, in_reply_to_status_id=in_reply_to_status_id,
            status="text")

  .. warning:: Either status or filename must be given.
  """
  try:
    if filename is None:
      if status is None:
        raise NameError("Neither status nor filename is defined")

      # Reply with text
      api.update_status(in_reply_to_status_id=in_reply_to_status_id,
                        status=status)
      LOGGER.info('-> Tweeted "%s"', status)

    elif status is None:
      # Reply with an image
      api.update_with_media(in_reply_to_status_id=in_reply_to_status_id,
                            filename=filename)
      LOGGER.info("-> Tweeted an image")

    else:
      # Reply with both text and an image
      api.update_with_media(in_reply_to_status_id=in_reply_to_status_id,
                            status=status, filename=filename)
      LOGGER.info('-> Tweeted "%s"', status)

    return

  except Exception as e:
    LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)
    return "Error"


if IS_TRAVIS_CI is True:
  LOGGER.info("Travis CI build succeeded.")
  sys.exit()

api = certify()

LOGGER.info("Authentication successful.")

MY_TWITTER_USERNAME = str(api.me().screen_name)
LOGGER.info("Hello @%s!", MY_TWITTER_USERNAME)

try:
  MY_STREAM = tweepy.Stream(auth=api.auth, listener=MyStreamListener())

  LOGGER.info("Started streaming...")

  MY_STREAM.userstream()

  LOGGER.info("Finished streaming.")

except Exception as e:
  LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)
