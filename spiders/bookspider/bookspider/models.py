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
    editor = StringField()
    credits = StringField()
    language = StringField()
    summary = StringField()
    release = DateTimeField()
    isbn_10 = StringField()
    subject = StringField()

    # Housekeeping fields
    url = StringField()
    sha = StringField()
    project = StringField()
    spider = StringField()
    server = StringField()
    date = DateTimeField(required=True)
