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

# Set the filetype to png
matplotlib.use(u"Agg")

logging.basicConfig(format=u"[%(filename)s:%(lineno)d] %(message)s")
LOGGER = logging.getLogger(
    os.path.splitext(os.path.basename(__file__))[0].decode("utf-8")
)
LOGGER.setLevel(logging.DEBUG)

IS_TRAVIS_CI = bool(len(sys.argv) == 2 and sys.argv[1] == "--travis")

if not IS_TRAVIS_CI:
    CONSUMER_KEY = os.environ["CONSUMER_KEY"].decode("utf_8")
    CONSUMER_SECRET = os.environ["CONSUMER_SECRET"].decode("utf_8")
    ACCESS_TOKEN = os.environ["ACCESS_TOKEN"].decode("utf_8")
    ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"].decode("utf_8")


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        if not is_mention_or_reply_to_me(status):
            return

        try:
            tweet_username = status.user.screen_name
            tweet_text = status.text
            tweet_id = status.id

            query = tweet_text.split(u" ", tweet_text.count(u"@"))[-1]

            searched_tweets = search_tweets(twi_api=api, query=query,
                                            max_tweets=500)

            LOGGER.info(u"-> %d tweets were found.", len(searched_tweets))

            # If the search didn't match any tweets, then tweeting that.
            # Note: If len(searched_tweets) == 0, then searched_tweets returns
            # False.
            if not searched_tweets:
                my_reply = u"@{0} Your search - {1} - did not match any twee" \
                           u"ts. Try different keywords."\
                    .format(tweet_username, query)

                reply(twi_api=api, in_reply_to_status_id=tweet_id,
                      status=my_reply)
                return

            stop_words = [u"てる", u"いる", u"なる", u"れる", u"する", u"ある",
                          u"こと", u"これ", u"さん", u"して", u"くれる", u"やる",
                          u"くださる", u"そう", u"せる", u"した", u"思う", u"それ",
                          u"ここ", u"ちゃん", u"くん", u"", u"て", u"に", u"を",
                          u"は", u"の", u"が", u"と", u"た", u"し", u"で", u"ない",
                          u"も", u"な", u"い", u"か", u"ので", u"よう", u"", u"RT",
                          u"@", u"http", u"https", u".", u":", u"/", u"//",
                          u"://"]

            # Append the query itself to stop words.
            query_surfaces = get_surfaces(query)
            stop_words.extend(query_surfaces)

            # Create words list.
            words = [tweet.text for tweet in searched_tweets]

            # Do morphological analysis using MeCab, and create a defaultdict
            # of words frequencies.
            frequencies = get_words_frequencies(words=words,
                                                stop_words=stop_words)

            image_path = u"/tmp/{0}.png".format(tweet_id)

            # Generate a wordcloud image.
            generate_wordcloud_image(frequencies=frequencies,
                                     image_path=image_path)

            my_reply = u'@{0} Search results for "{1}" (about {2} tweets)'\
                .format(tweet_username, query, len(searched_tweets))

            # Reply with the wordcloud image
            reply(twi_api=api, in_reply_to_status_id=tweet_id, status=my_reply,
                  filename=image_path)

        except Exception as e:
            LOGGER.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)

            my_reply = u"@{0} 500 Internal Server Error. Sorry, something " \
                       u"went wrong.".format(tweet_username)

            reply(twi_api=api, in_reply_to_status_id=tweet_id, status=my_reply)

        return

    def on_error(self, status_code):
        LOGGER.warning(u"Error")
        LOGGER.error(status_code)


def certify():
    """Authenticate with Twitter using Tweepy and return Twitter API object.

    :returns: Twitter API object
    :rtype: Twitter API object
    """
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    return api


def is_mention_or_reply_to_me(status):
    """Determine whether the tweet is a mention or a reply to me or not.

    :param status: A tweet status (required)
    :type status: A tweet object
    :returns: True if the tweet is a mention or a reply to me, otherwise False
    :rtype: bool
    """
    try:
        tweet_username = status.user.screen_name
        tweet_text = status.text

        LOGGER.info(u'@%s: "%s"', tweet_username, tweet_text)

        # If the tweet is a retweet, then skipped.
        if u"RT " in tweet_text:
            LOGGER.info(u"-> Skipped (a retweet).")
            return False

        # If the tweet is neither a mention nor a reply, then skipped.
        if status.in_reply_to_screen_name is None or u"@" not in tweet_text \
                or u" " not in tweet_text:
            LOGGER.info(u"-> Skipped (neither a mention nor a reply).")
            return False

        tweet_to = status.in_reply_to_screen_name

        # If the tweet is neither a mention nor a reply to me, then skipped.
        if tweet_to != MY_TWITTER_USERNAME:
            LOGGER.info(u"-> Skipped (neither a mention nor a reply to me).")
            return False

        return True

    except Exception as e:
        LOGGER.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)


def raise_exception_if_not_429_too_many_requests(e):
    """If the error is not the 429 Too Many Requests error, raise an error.
    Otherwise, passing.

    :param Exception e: A handled exception when using Tweepy (required)
    """
    if e.find(u"429") == -1:
        raise Exception(u"[line {0}] {1}".format(sys.exc_info()[-1].tb_lineno,
                                                 e))


def search_tweets(twi_api, query, max_tweets):
    """Search the tweets that match a search query and return them.

    :param twi_api: Twitter API object (required)
    :type twi_api: Twitter API obj
    :param unicode query: A search query (required)
    :param int max_tweets: The maximum search results limit (required)
    :returns: A list of SearchResult objects
    :rtype: list of SearchResult obj

    :Example:
    >>> search_tweets(twi_api=api, query=u"keyword", max_tweets=500)
    """
    query_encoded = urllib.quote_plus(query)

    while True:
        try:
            LOGGER.info(u'Searching "%s"...', query)

            result = [status for status in tweepy.Cursor(
                twi_api.search, q=query_encoded, lang=u"ja").items(max_tweets)]

            return result

        except Exception as e:
            # If the error is not the 429 Too Many Requests error, raise an
            # error. Otherwise, retrying in 1 minute.
            raise_exception_if_not_429_too_many_requests(e=e)

            LOGGER.warning(u"429 Too Many Requests. Waiting 1 minute...")
            time.sleep(60)


def get_surfaces(word):
    """Do morphological analysis using MeCab, and return list of surfaces.

    :param unicode word: A word whose surfaces we want to know (required)
    :return: list of surfaces
    :rtype: list of unicode

    :Example:
    >>> query_surfaces = get_surfaces(query)
    """
    return [node.surface.decode("utf_8")
            for node in MeCab().parse(word.encode("utf_8"), as_nodes=True)]


class Frequencies:
    """A class to generate a frequencies dict.

    :Example:
    >>> frequencies_obj = Frequencies()
    >>> frequencies_obj.add(node)
    >>> return frequencies_obj.dict
    """
    def __init__(self):
        """A method to initialize a object.
        """
        self.dict = defaultdict(int)

    def add(self, node):
        """Add text or its end-form to dict.

        :param node: A MeCabNode instance (required)
        :type node: MeCabNode instance obj
        """
        parts_of_speech = node.feature.decode("utf_8").split(u",")[0]
        word = node.surface.decode("utf-8")
        word_end_form = node.feature.decode("utf-8").split(u",")[6]

        # If the word is adjective or verb, then add its end-form to dict.
        if parts_of_speech == u"形容詞":
            self.dict[word_end_form] += 100
        elif parts_of_speech == u"動詞":
            self.dict[word_end_form] += 1
        elif parts_of_speech in [u"名詞", u"副詞"]:
            self.dict[word] += 1


def get_words_frequencies(words, stop_words):
    """Do morphological analysis using MeCab, and return a defaultdict of words
    frequencies.

    :param words: A list of word (required)
    :type words: list of unicode
    :param stop_words: Stop words (required)
    :type stop_words: list of unicode
    :return: A defaultdict of words frequencies
    :rtype: defaultdict

    :Example:
    >>> frequencies = get_words_frequencies(words=words, stop_words=stop_words)
    """
    LOGGER.info(u"Doing morphological analysis using MeCab...")

    # Concatenate words with spaces
    text = u" ".join(words)

    frequencies_obj = Frequencies()

    # Do morphological analysis using MeCab.
    for node in MeCab().parse(text.encode("utf_8"), as_nodes=True):
        # If the word is a stop word, then skipped.
        if node.surface.decode("utf_8") in stop_words:
            continue

        frequencies_obj.add(node)

    LOGGER.info(u"-> Done.")

    return frequencies_obj.dict


def reply(twi_api, in_reply_to_status_id, status, filename=None):
    """Reply with text, or with both text and an image

    :param twi_api: Twitter API object (required)
    :type twi_api: Twitter API object
    :param int in_reply_to_status_id: The ID of an existing status that the
                                      update is in reply to (required)
    :param unicode status: The text of your status update (required)
    :param unicode filename: The local path to image file to upload (optional)

    :Example:

    >>> reply(twi_api=api, in_reply_to_status_id=in_reply_to_status_id,
              status=u"text")
    """
    # Reply with text
    if filename is None:
        twi_api.update_status(in_reply_to_status_id=in_reply_to_status_id,
                              status=status)
        LOGGER.info(u'-> Tweeted "%s"', status)

    # Reply with both text and an image
    else:
        twi_api.update_with_media(in_reply_to_status_id=in_reply_to_status_id,
                                  status=status, filename=filename)
        LOGGER.info(u'-> Tweeted "%s"', status)

    return


def generate_wordcloud_image(frequencies, image_path):
    """Generate a wordcloud image from a defaultdict of words frequencies.

    :param defaultdict frequencies: A defaultdict of words frequencies
                                    (required)
    :param unicode image_path: The wordcloud image file path (required)

    :Example:
    >>> generate_wordcloud_image(frequencies=frequencies,
                                 image_path=image_path)
    """
    font_path = u"rounded-mplus-1p-bold.ttf"

    wordcloud = WordCloud(background_color=u"white", width=900, height=450,
                          font_path=font_path, min_font_size=12)

    LOGGER.info(u"Generating a wordcloud image...")

    image = wordcloud.generate_from_frequencies(frequencies=frequencies)

    image.to_file(filename=image_path)

    LOGGER.info(u'-> Saved a wordcloud image to "%s"', image_path)


if IS_TRAVIS_CI is True:
    LOGGER.info(u"Travis CI build succeeded.")
    sys.exit()

api = certify()

LOGGER.info(u"Authentication successful.")

MY_TWITTER_USERNAME = api.me().screen_name
LOGGER.info(u"Hello @%s!", MY_TWITTER_USERNAME)

try:
    MY_STREAM = tweepy.Stream(auth=api.auth, listener=MyStreamListener())

    LOGGER.info(u"Started streaming...")

    MY_STREAM.userstream()

    LOGGER.info(u"Finished streaming.")

except Exception as e:
    LOGGER.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)
