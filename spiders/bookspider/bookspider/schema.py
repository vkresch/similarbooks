import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType
from graphene import Connection, PageInfo
from app.similarbooks.main.constants import QUERY_LIMIT, IGNORE_FIELDS_FOR_FILTER
from .models import Book as BookModel


class Book(MongoengineObjectType):
    genres = graphene.List(graphene.String)

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
    title__exists = graphene.String(
        name="title_exists",
        description="Book title exists",
    )
    title__contains = graphene.String(
        name="title_contains",
        description="Books has to have ONE of the provided city",
    )
    summary__exists = graphene.Boolean(
        name="summary_exists",
    )
    summary__length_gte = graphene.Int(
        name="summary_length_gte",
        description="Filter books with summaries that have at least the specified number of characters.",
    )
    author = graphene.String(
        name="author",
        description="Book has to have ONE of the provided typ",
    )
    sha = graphene.String(
        name="sha",
    )
    language = graphene.String(
        name="language",
    )
    spider = graphene.String(
        name="spider",
    )


def convert_filters(filters):
    mongo_filters = {}
    for key, value in filters.items():
        if key.endswith("_lt"):
            field = key[:-4]
            if f"{field}__gt" in filters:
                mongo_filters[f"{field}"] = {
                    "$gt": filters[f"{field}__gt"],
                    "$lt": value,
                }
            else:
                mongo_filters[f"{field}"] = {"$lt": value}
        elif key.endswith("_lte"):
            field = key[:-5]
            if f"{field}__gte" in filters:
                mongo_filters[f"{field}"] = {
                    "$gte": filters[f"{field}__gte"],
                    "$lte": value,
                }
            else:
                mongo_filters[f"{field}"] = {"$lte": value}
        elif key.endswith("_gt"):
            field = key[:-4]
            if f"{field}__lt" in filters:
                mongo_filters[f"{field}"] = {
                    "$gt": value,
                    "$lt": filters[f"{field}__lt"],
                }
            else:
                mongo_filters[f"{field}"] = {"$gt": value}
        elif key.endswith("_gte"):
            field = key[:-5]
            if f"{field}__lte" in filters:
                mongo_filters[f"{field}"] = {
                    "$gte": value,
                    "$lte": filters[f"{field}__lte"],
                }
            else:
                mongo_filters[f"{field}"] = {"$gte": value}
        elif key.endswith("__in"):
            field = key[:-4]
            if isinstance(value, list):
                mongo_filters[f"{field}"] = {"$in": value}
            else:
                mongo_filters[f"{field}"] = {"$in": [value]}
        elif key.endswith("__exists"):
            field = key[:-8]
            mongo_filters[f"{field}"] = {"$exists": value}
        elif key.endswith("__contains"):
            field = key[:-10]
            mongo_filters[f"{field}"] = {"$regex": value, "$options": "i"}
        elif key.endswith("__ne"):
            field = key[:-4]
            mongo_filters[f"{field}"] = {"$ne": value}
        else:
            mongo_filters[f"{key}"] = value
    return mongo_filters


def transform(prop, document):
    return document(**{key: value for key, value in prop.items()})


def get_sort_args(sort_string):
    # Check if the string starts with "-" or "+"
    if sort_string.startswith("-"):
        field_name = sort_string[1:]
        sort_order = -1
    elif sort_string.startswith("+"):
        field_name = sort_string[1:]
        sort_order = 1
    else:
        field_name = sort_string
        sort_order = 1

    return {field_name: sort_order}


def update_filter(filters, kwargs):
    for key, value in kwargs.items():
        if key in IGNORE_FIELDS_FOR_FILTER:
            continue

        # Enable regex search for those fields
        if key in ["title", "summary"]:
            key = f"{key}__contains"

        filters[key] = value
    return filters


def common_resolver(**kwargs):
    per_page = min(kwargs.get("per_page", QUERY_LIMIT), QUERY_LIMIT)
    offset = (kwargs.get("page", 1) - 1) * per_page
    order_by = kwargs.get("order_by", "_id")
    filters = update_filter(kwargs.get("filters", {}), kwargs)

    # Check if the `summary__length_gte` filter is provided
    summary_length_filter = filters.pop("summary__length_gte", None)

    pipeline = [
        {"$match": convert_filters(filters)},  # Apply other filters
    ]

    # If a summary length filter is provided, apply it
    if summary_length_filter is not None:
        pipeline.append(
            {
                "$match": {
                    "$and": [
                        {"summary": {"$exists": True}},  # Check if summary exists
                        {
                            "$expr": {
                                "$gte": [
                                    {
                                        "$strLenCP": {
                                            "$ifNull": [
                                                "$summary",
                                                "",
                                            ]  # Ensure summary is not null
                                        }
                                    },
                                    summary_length_filter,
                                ]
                            }
                        },
                    ]
                }
            }
        )

    pipeline.extend(
        [
            {"$sort": get_sort_args(order_by)},  # Sorting
            {"$skip": offset},  # Pagination: skip first `offset` documents
            {"$limit": per_page},  # Limit the number of documents returned
            {"$project": {"_id": 0}},  # Don't return the `_id` field
        ]
    )

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
        page=graphene.Int(),
        per_page=graphene.Int(),
        order_by=graphene.String(),
    )

    def resolve_all_books(self, info, **kwargs):
        return common_resolver(model=BookModel, document=Book, **kwargs)
