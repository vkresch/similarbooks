# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class BookItem(Item):
    book_id = Field()
    title = Field()
    author = Field()
    author_url = Field()
    editor = Field()
    credits = Field()
    summary = Field()
    language = Field()
    release = Field()
    isbn_10 = Field()
    subject = Field()

    # Housekeeping fields
    url = Field()
    sha = Field()
    project = Field()
    spider = Field()
    server = Field()
    date = Field()
