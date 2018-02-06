from wordcloud import WordCloud

from logger import logger


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
