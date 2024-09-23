import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType
from graphene import Connection, PageInfo
from app.similarbooks.main.constants import (
    QUERY_LIMIT,
)
from .models import Book as BookModel


class Book(MongoengineObjectType):
    class Meta:
        description = "Book"
        model = BookModel
        interfaces = (Node,)


class BookFilter(graphene.InputObjectType):
    # Query operators
    # https://www.mongodb.com/docs/manual/reference/operator/query-logical/
    book_id = graphene.String(
        name="book_id",
    )
    book_id__in = graphene.List(
        graphene.String,
        name="book_id_in",
        description="Book has to have ONE of the provided book_id",
    )
    book_id__all = graphene.List(
        graphene.String,
        name="book_id_all",
        description="Book has to have all provided book_id",
    )
    title = graphene.String(
        name="title",
        description="Book has to have ONE of the provided title",
    )
    author = graphene.String(
        name="author",
        description="Book has to have ONE of the provided typ",
    )


def common_resolver(**kwargs):
    pipeline = [
        {"$match": convert_filters(filters)},  # Apply the filters in the pipeline
        {"$sort": get_sort_args(order_by)},  # 1 for ascending, -1 for descending
        {"$skip": offset},  # Add this stage to skip the first 5 documents
        {"$limit": per_page},  # Add this stage to limit the result to 10 documents
        {"$project": {"_id": 0}},
    ]
    return list(
        map(
            lambda prop: transform(prop, kwargs.get("document")),
            BookModel.objects.aggregate(*pipeline),
        )
    )


class Query(graphene.ObjectType):
    class Meta:
        description = "Root Query"

    node = Node.Field(Book)
    all_books = MongoengineConnectionField(
        Book,
        filters=BookFilter(),
    )

    def resolve_all_books(self, info, **kwargs):
        return common_resolver(model=BookModel, document=Book, **kwargs)
