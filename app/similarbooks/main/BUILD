load("@py_deps//:requirements.bzl", "requirement")

py_library(
    name = "main",
    srcs = [
        "forms.py",
        "routes.py",
        "utils.py",
        "common.py",
    ],
    deps = [
        requirement("flask"),
        requirement("flask_caching"),
        requirement("plotly"),
        requirement("requests"),
        requirement("somoclu"),
        requirement("pandas"),
        "//som:utils",
        "//app/similarbooks:similarbooks_config",
        ":constants",
    ],
    visibility = ["//app:__subpackages__"],
)

py_library(
    name = "constants",
    srcs = [
        "constants.py",
    ],
    visibility = ["//visibility:public"],
)