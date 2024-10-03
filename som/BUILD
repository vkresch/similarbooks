load("@py_deps//:requirements.bzl", "requirement")

filegroup(
    name = "models",
    srcs = glob([
        "models/*.pkl",
    ]),
    visibility = ["//visibility:public"],
)

py_library(
    name = "utils",
    srcs = ["Scaler.py", "utils.py"],
    data = [":models"],
    deps = [
        requirement("requests"),
        requirement("scikit-learn"),
        requirement("pymongo"),
        requirement("tqdm"),
        "//app/similarbooks:similarbooks_config",
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "generate_sitemaps",
    main = "generate_sitemaps.py",
    srcs = ["generate_sitemaps.py"],
    deps = [
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "predict",
    main = "predict.py",
    srcs = ["predict.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        requirement("dash"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "show_websom",
    main = "show_websom.py",
    srcs = ["show_websom.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        requirement("dash"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "show_wordcategory",
    main = "show_wordcategory.py",
    srcs = ["show_wordcategory.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        requirement("dash"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "download_books",
    main = "download_books.py",
    srcs = ["download_books.py"],
    deps = [
        requirement("somoclu"),
        requirement("plotly"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        requirement("beautifulsoup4"),
        requirement("pillow"),
        "//app/similarbooks/main:constants",
        "//app/similarbooks:similarbooks_config",
        ":utils",
    ],
)

py_binary(
    name = "train_lda",
    main = "train_lda.py",
    srcs = ["train_lda.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "train_lda_websom",
    main = "train_lda_websom.py",
    srcs = ["train_lda_websom.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "train_wordcategory_map",
    main = "train_wordcategory_map.py",
    srcs = ["train_wordcategory_map.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "train_websom",
    main = "train_websom.py",
    srcs = ["train_websom.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)