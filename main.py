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

matplotlib.use('Agg')  # Set the filetype to png

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

        searched_tweets = search_tweets(twi_api=api, query=query,
                                        max_tweets=500)

        LOGGER.info('-> %d tweets were found.', len(searched_tweets))

        # If the search didn't match any tweets, then tweeting that.
        # If len(searched_tweets) == 0, then searched_tweets returns False.
        if not searched_tweets:
          my_reply = "@{0} Your search - {1} - did not match any tweets. Try \
                     different keywords.".format(tweet_username, query)

          reply(twi_api=api, in_reply_to_status_id=tweet_id, status=my_reply)
          return

        frequency = do_morphological_analysis(searched_tweets=searched_tweets,
                                              query=query)

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

        reply(twi_api=api, in_reply_to_status_id=tweet_id, status=my_reply,
              filename=file_path)

      except Exception as e:
        LOGGER.error("[line %s] %s", sys.exc_info()[-1].tb_lineno, e)

        my_reply = "@{0} 500 Internal Server Error. Sorry, something went wrong.".format(tweet_username)

        reply(twi_api=api, in_reply_to_status_id=tweet_id, status=my_reply)

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


def search_tweets(twi_api, query, max_tweets):
  """
  Search the tweets that match a search query and return them.

  :param twi_api: Twitter API object (required)
  :type twi_api: Twitter API obj
  :param str query: A search query (required)
  :param int max_tweets: The maximum search results limit (required)
  :returns: A list of SearchResult objects
  :rtype: list of SearchResult obj

  :Example:
  >>> search_tweets(twi_api=api, query="keyword", max_tweets=500)
  """
  query_encoded = urllib.quote_plus(query)

  while True:
    try:
      LOGGER.info('Searching "%s"...', query)

      result = [status for status in tweepy.Cursor(
          twi_api.search, q=query_encoded, lang="ja").items(max_tweets)]

      return result
    except Exception as e:
      # If the error is not the 429 Too Many Requests error, raise an error.
      # Otherwise, retrying in 1 minute.
      if str(e).find("429") == -1:
        raise Exception("[line {0}] {1}".format(sys.exc_info()[-1].tb_lineno,
                                                e))

      LOGGER.warning("429 Too Many Requests. Waiting 1 minute...")
      time.sleep(60)


def do_morphological_analysis(searched_tweets, query):
  """
  Do morphological analysis using MeCab, and return a defaultdict of word
  frequency.

  :param searched_tweets: A list of SearchResult objects (required)
  :type searched_tweets: list of SearchResult obj
  :param str query: A search query (required)
  :return: A defaultdict of word frequency
  :rtype: defaultdict

  :Example:
  >>> frequency = do_morphological_analysis(searched_tweets=searched_tweets,
                                            query=query)
  """
  stop_words = ['てる', 'いる', 'なる', 'れる', 'する', 'ある', 'こと', 'これ', 'さん',
                'して', 'くれる', 'やる', 'くださる', 'そう', 'せる', 'した', '思う',
                'それ', 'ここ', 'ちゃん', 'くん', '', 'て', 'に', 'を', 'は', 'の',
                'が', 'と', 'た', 'し', 'で', 'ない', 'も', 'な', 'い', 'か', 'ので',
                'よう', '', 'RT', '@', 'http', 'https', '.', ':', '/', '//',
                '://']

  # Append the query itself to stop words.
  with MeCab() as nm:
    for node in nm.parse(query, as_nodes=True):
      word = node.surface
      stop_words.append(word)

  LOGGER.info("Doing morphological analysis using MeCab...")

  frequency = defaultdict(int)

  # Do morphological analysis using MeCab.
  for tweet in searched_tweets:
    text = str(tweet.text.encode("utf-8"))

    with MeCab() as nm:
      for node in nm.parse(text, as_nodes=True):
        word = node.surface

        # If the word is a stop word, then skipping.
        if word in stop_words:
          continue

        word_type = node.feature.split(",")[0]
        word_decoded = node.surface.decode('utf-8')
        word_original_form_decoded = node.feature.split(",")[6].decode('utf-8')

        # If the word is adjective or verb, then add its original form to dict.
        if word_type == "形容詞":
          frequency[word_original_form_decoded] += 100
        elif word_type == "動詞":
          frequency[word_original_form_decoded] += 1
        elif word_type in ["名詞", "副詞"]:
          frequency[word_decoded] += 1

  LOGGER.info("-> Done.")

  return frequency


def reply(twi_api, in_reply_to_status_id, status, filename=None):
  """
  Reply with text, or with both text and an image

  :param twi_api: Twitter API object (required)
  :type twi_api: Twitter API object
  :param int in_reply_to_status_id: The ID of an existing status that the updatez
    is in reply to (required)
  :param str status: The text of your status update (required)
  :param str filename: The local path to image file to upload (optional)

  :Example:

  >>> reply(twi_api=api, in_reply_to_status_id=in_reply_to_status_id,
            status="text")
  """
  # Reply with text
  if filename is None:
    twi_api.update_status(in_reply_to_status_id=in_reply_to_status_id,
                          status=status)
    LOGGER.info('-> Tweeted "%s"', status)

  # Reply with both text and an image
  else:
    twi_api.update_with_media(in_reply_to_status_id=in_reply_to_status_id,
                              status=status, filename=filename)
    LOGGER.info('-> Tweeted "%s"', status)

  return


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
