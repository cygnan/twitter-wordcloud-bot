#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import matplotlib
import tweepy

from logger import logger
from mecab import get_surfaces, get_words_frequencies
from tweepy_handler import certify, is_mention_or_reply_to_me, search_tweets, \
    reply
from wordcloud_handler import generate_wordcloud_image

# Set the filetype to png
matplotlib.use(u"Agg")


class TweetHandler:
    def __init__(self, api, status):
        self.api = api
        self.status = status
        self.tweet_username = self.status.user.screen_name
        self.tweet_text = self.status.text
        self.tweet_id = self.status.id

    def process(self):
        if not is_mention_or_reply_to_me(api=self.api, status=self.status):
            return

        try:
            query = self.tweet_text.split(u" ", self.tweet_text.count(u"@"))[-1]

            searched_tweets = search_tweets(api=self.api, query=query,
                                            max_tweets=500)

            # If the search didn't match any tweets, then tweeting that.
            # Note: If len(searched_tweets) == 0, then searched_tweets returns
            # False.
            if not searched_tweets:
                my_reply = u"@{0} Your search - {1} - did not match any twee" \
                           u"ts. Try different keywords."\
                    .format(self.tweet_username, query)

                reply(api=self.api, in_reply_to_status_id=self.tweet_id,
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

            image_path = u"/tmp/{0}.png".format(self.tweet_id)

            # Generate a wordcloud image.
            generate_wordcloud_image(frequencies=frequencies,
                                     image_path=image_path)

            my_reply = u'@{0} Search results for "{1}" (about {2} tweets)'\
                .format(self.tweet_username, query, len(searched_tweets))

            # Reply with the wordcloud image
            reply(api=self.api, in_reply_to_status_id=self.tweet_id,
                  status=my_reply, filename=image_path)

        except Exception as e:
            self.handle_exception(e=e)

    def handle_exception(self, e):
        logger.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)

        my_reply = u"@{0} 500 Internal Server Error. Sorry, something " \
                   u"went wrong.".format(self.tweet_username)

        reply(api=self.api, in_reply_to_status_id=self.tweet_id,
              status=my_reply)


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        tweet_handler = TweetHandler(api=self.api, status=status)
        tweet_handler.process()

    def on_error(self, status_code):
        logger.warning(u"Error")
        logger.error(status_code)


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--travis":
        logger.info(u"Travis CI build succeeded.")
        sys.exit()

    api = certify()

    logger.info(u"Authentication successful.")

    my_twitter_username = api.me().screen_name
    logger.info(u"Hello @%s!", my_twitter_username)

    try:
        my_stream_listener = MyStreamListener(api=api)
        my_stream = tweepy.Stream(auth=api.auth, listener=my_stream_listener)

        logger.info(u"Started streaming...")
        my_stream.userstream()

        logger.info(u"Finished streaming.")

    except Exception as e:
        logger.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)


if __name__ == "__main__":
    main()
