load("@py_deps//:requirements.bzl", "requirement")

py_library(
    name = "schemas",
    srcs = [
        "bookspider/schema.py", 
        "bookspider/models.py"
    ],
    deps = [
        requirement("graphene"),
        requirement("graphene_mongo")
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bookspider",
    main = "main.py",
    srcs = ["main.py"],
    deps = [
        requirement("scrapy"),
        requirement("tqdm"),
        "//som:utils",
        "//app/similarbooks/main:constants",
        ":schemas",
    ],
)
