#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

import matplotlib
import tweepy
from natto import MeCab
from wordcloud import WordCloud

from logger import logger
from tweepy_handler import certify, is_mention_or_reply_to_me, search_tweets, \
    reply

# Set the filetype to png
matplotlib.use(u"Agg")


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        if not is_mention_or_reply_to_me(api=self.api, status=status):
            return

        try:
            tweet_username = status.user.screen_name
            tweet_text = status.text
            tweet_id = status.id

            query = tweet_text.split(u" ", tweet_text.count(u"@"))[-1]

            searched_tweets = search_tweets(api=self.api, query=query,
                                            max_tweets=500)

            logger.info(u"-> %d tweets were found.", len(searched_tweets))

            # If the search didn't match any tweets, then tweeting that.
            # Note: If len(searched_tweets) == 0, then searched_tweets returns
            # False.
            if not searched_tweets:
                my_reply = u"@{0} Your search - {1} - did not match any twee" \
                           u"ts. Try different keywords."\
                    .format(tweet_username, query)

                reply(api=self.api, in_reply_to_status_id=tweet_id,
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
            reply(api=self.api, in_reply_to_status_id=tweet_id,
                  status=my_reply, filename=image_path)

        except Exception as e:
            logger.error(u"[line %d] %s", sys.exc_info()[-1].tb_lineno, e)

            my_reply = u"@{0} 500 Internal Server Error. Sorry, something " \
                       u"went wrong.".format(tweet_username)

            reply(api=self.api, in_reply_to_status_id=tweet_id,
                  status=my_reply)

        return

    def on_error(self, status_code):
        logger.warning(u"Error")
        logger.error(status_code)


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
        """A method to initialize a object."""
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
    logger.info(u"Doing morphological analysis using MeCab...")

    # Concatenate words with spaces
    text = u" ".join(words)

    frequencies_obj = Frequencies()

    # Do morphological analysis using MeCab.
    for node in MeCab().parse(text.encode("utf_8"), as_nodes=True):
        # If the word is a stop word, then skipped.
        if node.surface.decode("utf_8") in stop_words:
            continue

        frequencies_obj.add(node)

    logger.info(u"-> Done.")

    return frequencies_obj.dict


def generate_wordcloud_image(frequencies, image_path):
    """Generate a wordcloud image from a defaultdict of words frequencies.

    :param defaultdict frequencies: A defaultdict of words frequencies
                                    (required)
    :param unicode image_path: The wordcloud image file path (required)

    :Example:
    >>> generate_wordcloud_image(frequencies=frequencies,
    >>>                          image_path=image_path)
    """
    font_path = u"rounded-mplus-1p-bold.ttf"

    wordcloud = WordCloud(background_color=u"white", width=900, height=450,
                          font_path=font_path, min_font_size=12)

    logger.info(u"Generating a wordcloud image...")

    image = wordcloud.generate_from_frequencies(frequencies=frequencies)

    image.to_file(filename=image_path)

    logger.info(u'-> Saved a wordcloud image to "%s"', image_path)


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
