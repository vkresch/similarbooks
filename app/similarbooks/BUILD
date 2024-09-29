load("@py_deps//:requirements.bzl", "requirement")

filegroup(
    name = "templates",
    srcs = [
        "templates/home.html",
        "templates/detailed.html",
         "templates/not_found.html",
        "templates/layout.html",
        "templates/about.html",
        "templates/impressum.html",
        "templates/datenschutz.html",
        "static/css/default.css",
        "static/robots.txt",
        "static/sitemap.xml",
        "static/scss/_custom.scss",
        "static/scss/_variables.scss",
        "static/favicon.ico",
    ],
)

filegroup(
    name = "profile_pics",
    srcs = ["static/profile_pics/default.png"],
)

py_library(
    name = "similarbooks_lib",
    srcs = [
        "__init__.py",
    ],
    deps = [
        requirement("graphene"),
        ":similarbooks_config",
        "//app/similarbooks/main:main",
    ],
    data = [":templates", ":profile_pics"],
    visibility = ["//app:__subpackages__"],
)

py_library(
        name = "similarbooks_config",
    srcs = [
        "config.py",
    ],
    visibility = ["//visibility:public"],
)
