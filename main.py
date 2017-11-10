#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import sys
import urllib
import tweepy
from wordcloud import WordCloud
from natto import MeCab

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

      LOGGER.info('@{0}: "{1}"'.format(tweet_username, tweet_text))


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
            query = tweet_text.split(" ", tweet_text.count("@"))[-1]
            query_encoded = urllib.quote_plus(query)

            from collections import defaultdict
            frequency = defaultdict(int)

            LOGGER.info('Searching "{0}"...'.format(query))
            MAX_TWEETS = 1000
            searched_tweets = [status for status in tweepy.Cursor(
                API.search, q=query_encoded).items(MAX_TWEETS)]
            LOGGER.info(
                '-> {0} tweets were found.'.format(str(len(searched_tweets))))

            no_hit = len(searched_tweets) == 0
            if no_hit:
              my_reply = "@{0} Your search - {1} - did not match any tweets. Try different keywords.".format(tweet_username, query)

              API.update_status(status=my_reply, in_reply_to_status_id=tweet_id)

              LOGGER.info('-> Tweeted "{0}"'.format(my_reply))
            else:
              LOGGER.info("Generating a wordcloud image...")

              for tweet in searched_tweets:
                text = str(tweet.text.encode("utf-8"))
                # filter(tweet.text.encode("utf-8"))

                with MeCab() as nm:
                  for node in nm.parse(text, as_nodes=True):
                    word_type = node.feature.split(",")[0]
                    if word_type == "形容詞":
                      word = node.surface
                      frequency[word] += 10
                    elif word_type in ["動詞", "名詞", "副詞"]:
                      word = node.surface
                      frequency[word] += 1

              word_list = " ".join(frequency).decode('utf-8')

              fpath = "GenShinGothic-P-Normal.ttf"

              # stop_words = [ u'てる', u'いる', u'なる', u'れる', u'する', u'ある', u'こと',\
              #        u'これ', u'さん', u'して', u'くれる', u'やる', u'くださる',\
              #        u'そう', u'せる', u'した',  u'思う', u'それ', u'ここ', u'ちゃん',\
              #        u'くん', u'', u'て',u'に',u'を',u'は',u'の', u'が', u'と', u'た',\
              #        u'し', u'で', u'ない', u'も', u'な', u'い', u'か', u'ので',\
              #        u'よう', u'']
              stop_words = ['てる', 'いる', 'なる', 'れる', 'する', 'ある', 'こと',
                'これ', 'さん', 'して', 'くれる', 'やる', 'くださる',
                'そう', 'せる', 'した',  '思う', 'それ', 'ここ', 'ちゃん',
                'くん', '', 'て', 'に', 'を', 'は', 'の', 'が', 'と', 'た',
                'し', 'で', 'ない', 'も', 'な', 'い', 'か', 'ので',
                'よう', '']

              wordcloud = WordCloud(background_color="white", width=900,
                                    height=450, font_path=fpath,
                                    stopwords=set(stop_words))
              wordcloud_image = wordcloud.generate_from_frequencies(
                  frequencies=frequency)

              file_path = "/tmp/{0}.png".format(str(tweet_id))
              wordcloud_image.to_file(file_path)
              LOGGER.info('Saved a wordcloud image to "{0}"'.format(file_path))

              my_reply = '@{0} Search results for "{1}" (about {2} tweets)'.format(
                  tweet_username, query, str(len(searched_tweets)))  # Test

              API.update_with_media(filename=file_path, status=my_reply,
                                    in_reply_to_status_id=tweet_id)

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
