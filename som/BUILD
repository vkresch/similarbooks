load("@py_deps//:requirements.bzl", "requirement")

py_library(
    name = "utils",
    srcs = ["Scaler.py", "utils.py"],
    deps = [
        requirement("geopy"),
        requirement("requests"),
        requirement("scikit-learn"),
        requirement("pymongo"),
        "//app/similarbooks:similarbooks_config",
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "train",
    main = "train.py",
    srcs = ["train.py"],
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        requirement("matplotlib"),
        "//app/similarbooks/main:constants",
        "//app/similarbooks:similarbooks_config",
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
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)

py_binary(
    name = "visualize",
    main = "visualize.py",
    srcs = ["visualize.py"],
    deps = [
        requirement("somoclu"),
        requirement("plotly"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        "//app/similarbooks/main:constants",
        "//app/similarbooks:similarbooks_config",
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
        "//app/similarbooks/main:constants",
        "//app/similarbooks:similarbooks_config",
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
        requirement("nltk"),
        "//app/similarbooks/main:constants",
        ":utils",
    ],
)