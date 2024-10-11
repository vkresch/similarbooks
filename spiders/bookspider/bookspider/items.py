# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field
from scrapy.loader.processors import Identity


class BookItem(Item):
    book_id = Field()
    title = Field()
    author = Field()
    author_url = Field()
    author_image_url = Field()
    author_follower_count = Field()
    author_description = Field()
    is_gr_author = Field()
    editor = Field()
    credits = Field()
    summary = Field()
    image_url = Field()
    genres = Field(output_processor=Identity())
    num_pages = Field()
    format = Field()
    language = Field()
    release = Field()
    isbn_10 = Field()
    subject = Field()
    web_url = Field()
    series_position = Field()
    is_series = Field()

    # Stats
    average_rating = Field()
    ratings_count = Field()
    rating_one_count = Field()
    rating_two_count = Field()
    rating_three_count = Field()
    rating_four_count = Field()
    rating_five_count = Field()
    text_reviews_count = Field()

    # Links
    kindle_link = Field()
    amazon_link = Field()
    audible_link = Field()
    barnes_and_noble_link = Field()
    abe_books_link = Field()
    kobo_link = Field()
    google_play_link = Field()
    alibris_link = Field()
    indigo_link = Field()
    better_world_books_link = Field()
    indie_bounds_link = Field()
    thrift_books_link = Field()

    # Housekeeping fields
    url = Field()
    sha = Field()
    project = Field()
    spider = Field()
    server = Field()
    date = Field()

    # Model specific fields
    bmu_col = Field()
    bmu_row = Field()
