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
    sha__in = graphene.List(
        graphene.String,
        name="sha_in",
        description="Book has to have ONE of the provided sha",
    )
    language = graphene.String(
        name="language",
    )
    spider = graphene.String(
        name="spider",
    )
    bmu_col = graphene.Int(
        name="bmu_col",
    )
    bmu_col__exists = graphene.Boolean(
        name="bmu_col_exists",
    )
    bmu_row = graphene.Int(
        name="bmu_row",
    )
    bmu_row__exists = graphene.Boolean(
        name="bmu_row_exists",
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
            mongo_filters["$text"] = {
                "$search": '"' + value + '"',
            }
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


ignore_dict = {
    "_id": 0,
    "amazon_link": 0,
    "kindle_link": 0,
    "audible_link": 0,
    "barnes_and_noble_link": 0,
    "abe_books_link": 0,
    "kobo_link": 0,
    "google_play_link": 0,
    "alibris_link": 0,
    "indigo_link": 0,
    "better_world_books_link": 0,
    "indie_bounds_link": 0,
    "thrift_books_link": 0,
    "spider": 0,
    "project": 0,
    "image_url": 0,
    "server": 0,
    "date": 0,
    "author_image_url": 0,
}


def common_resolver(**kwargs):
    per_page = min(kwargs.get("per_page", QUERY_LIMIT), QUERY_LIMIT)
    offset = (kwargs.get("page", 1) - 1) * per_page
    order_by = kwargs.get("order_by", None)
    filters = update_filter(kwargs.get("filters", {}), kwargs)
    rapid_api_request = kwargs.get("rapid_api_request", None)

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

    if order_by is not None:
        pipeline.extend([{"$sort": get_sort_args(order_by)}])

    pipeline.extend(
        [
            # {"$skip": offset},  # Pagination: skip first `offset` documents
            {"$limit": per_page},  # Limit the number of documents returned
            {
                "$project": ({"_id": 0} if rapid_api_request is None else ignore_dict)
            },  # Don't return the `_id` field
        ]
    )

    return list(
        map(
            lambda prop: transform(prop, kwargs.get("document")),
            BookModel.objects.aggregate(*pipeline),
        )
    )


def random_resolver(**kwargs):
    order_by = kwargs.get("order_by", None)
    rapid_api_request = kwargs.get("rapid_api_request", None)

    pipeline = [
        {"$sample": {"size": 10}},
    ]

    if order_by is not None:
        pipeline.extend([{"$sort": get_sort_args(order_by)}])

    pipeline.extend(
        [
            {
                "$project": ({"_id": 0} if rapid_api_request is None else ignore_dict)
            },  # Don't return the `_id` field
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
        rapid_api_request = info.context["request"].headers.get(
            "X-Rapidapi-Request-Id", None
        )
        return common_resolver(
            model=BookModel,
            document=Book,
            rapid_api_request=rapid_api_request,
            **kwargs,
        )

    random_books = MongoengineConnectionField(
        Book,
        order_by=graphene.String(),
    )

    def resolve_random_books(self, info, **kwargs):
        rapid_api_request = info.context["request"].headers.get(
            "X-Rapidapi-Request-Id", None
        )
        return random_resolver(
            model=BookModel,
            document=Book,
            rapid_api_request=rapid_api_request,
            **kwargs,
        )
