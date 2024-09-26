from mongoengine import Document
from mongoengine.fields import (
    DateTimeField,
    StringField,
    FloatField,
    IntField,
    BooleanField,
    ListField,
)


class Book(Document):
    book_id = StringField(required=True)
    title = StringField()
    author = StringField()
    author_url = StringField()
    author_image_url = StringField()
    author_follower_count = IntField()
    author_description = StringField()
    is_gr_author = BooleanField()
    editor = StringField()
    credits = StringField()
    language = StringField()
    summary = StringField()
    image_url = StringField()
    genres = ListField(StringField)
    num_pages = IntField()
    format = StringField()
    release = DateTimeField()
    isbn_10 = StringField()
    subject = StringField()
    web_url = StringField()
    series_position = IntField()
    is_series = BooleanField()

    # Stats
    average_rating = FloatField()
    ratings_count = IntField()
    rating_one_count = IntField()
    rating_two_count = IntField()
    rating_three_count = IntField()
    rating_four_count = IntField()
    rating_five_count = IntField()
    text_reviews_count = IntField()

    # Links
    kindle_link = StringField()
    amazon_link = StringField()
    audible_link = StringField()
    barnes_and_noble_link = StringField()
    abe_books_link = StringField()
    kobo_link = StringField()
    google_play_link = StringField()
    alibris_link = StringField()
    indigo_link = StringField()
    better_world_books_link = StringField()
    indie_bounds_link = StringField()
    thrift_books_link = StringField()

    # Housekeeping fields
    url = StringField()
    sha = StringField()
    project = StringField()
    spider = StringField()
    server = StringField()
    date = DateTimeField(required=True)
