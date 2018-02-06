#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
from natto import MeCab

from logger import logger


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
