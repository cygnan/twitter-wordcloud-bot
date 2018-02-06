import sys
import urllib

import time

import os
import tweepy

from logger import logger


def certify():
    """Authenticate with Twitter using Tweepy and return Twitter API object.

    :returns: Twitter API object
    :rtype: Twitter API object
    """
    consumer_key = os.environ["CONSUMER_KEY"].decode("utf_8")
    consumer_secret = os.environ["CONSUMER_SECRET"].decode("utf_8")
    access_token = os.environ["ACCESS_TOKEN"].decode("utf_8")
    access_token_secret = os.environ["ACCESS_TOKEN_SECRET"].decode("utf_8")

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    return api


def is_mention_or_reply_to_me(api, status):
    """Determine whether the tweet is a mention or a reply to me or not.

    :param api: Twitter API object (required)
    :type api: Twitter API obj
    :param status: A tweet status (required)
    :type status: A tweet object
    :returns: True if the tweet is a mention or a reply to me, otherwise False
    :rtype: bool
    """
    try:
        tweet_username = status.user.screen_name
        tweet_text = status.text
        my_twitter_username = api.me().screen_name

        logger.info(u'@%s: "%s"', tweet_username, tweet_text)

        # If the tweet is a retweet, then skipped.
        if u"RT " in tweet_text:
            logger.info(u"-> Skipped (a retweet).")
            return False

        # If the tweet is neither a mention nor a reply, then skipped.
        if status.in_reply_to_screen_name is None or u"@" not in tweet_text \
                or u" " not in tweet_text:
            logger.info(u"-> Skipped (neither a mention nor a reply).")
            return False

        tweet_to = status.in_reply_to_screen_name

        # If the tweet is neither a mention nor a reply to me, then skipped.
        if tweet_to != my_twitter_username:
            logger.info(u"-> Skipped (neither a mention nor a reply to me).")
            return False

        return True

    except Exception as e:
        logger.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)


def raise_exception_if_not_429_too_many_requests(e):
    """If the error is not the 429 Too Many Requests error, raise an error.
    Otherwise, passing.

    :param Exception e: A handled exception when using Tweepy (required)
    """
    if e.find(u"429") == -1:
        raise Exception(u"[line {0}] {1}".format(sys.exc_info()[-1].tb_lineno,
                                                 e))


def search_tweets(api, query, max_tweets):
    """Search the tweets that match a search query and return them.

    :param api: Twitter API object (required)
    :type api: Twitter API obj
    :param unicode query: A search query (required)
    :param int max_tweets: The maximum search results limit (required)
    :returns: A list of SearchResult objects
    :rtype: list of SearchResult obj

    :Example:
    >>> search_tweets(api=api, query=u"keyword", max_tweets=500)
    """
    query_encoded = urllib.quote_plus(query.encode("utf_8")).decode("utf_8")

    while True:
        try:
            logger.info(u'Searching "%s"...', query)

            searched_tweets = [status for status in tweepy.Cursor(
                api.search, q=query_encoded, lang=u"ja").items(max_tweets)]

            logger.info(u"-> %d tweets were found.", len(searched_tweets))

            return searched_tweets

        except Exception as e:
            # If the error is not the 429 Too Many Requests error, raise an
            # error. Otherwise, retrying in 1 minute.
            raise_exception_if_not_429_too_many_requests(e=e)

            logger.warning(u"429 Too Many Requests. Waiting 1 minute...")
            time.sleep(60)


def reply(api, in_reply_to_status_id, status, filename=None):
    """Reply with text, or with both text and an image

    :param api: Twitter API object (required)
    :type api: Twitter API object
    :param int in_reply_to_status_id: The ID of an existing status that the
                                      update is in reply to (required)
    :param unicode status: The text of your status update (required)
    :param unicode filename: The local path to image file to upload (optional)

    :Example:

    >>> reply(api=api, in_reply_to_status_id=in_reply_to_status_id,
    >>>       status=u"text")
    """
    # Reply with text
    if filename is None:
        api.update_status(in_reply_to_status_id=in_reply_to_status_id,
                          status=status)
        logger.info(u'-> Tweeted "%s"', status)

    # Reply with both text and an image
    else:
        api.update_with_media(in_reply_to_status_id=in_reply_to_status_id,
                              status=status, filename=filename)
        logger.info(u'-> Tweeted "%s"', status)
