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
        "templates/account.html",
        "templates/login.html",
        "templates/register.html",
        "templates/reset_request.html",
        "templates/reset_token.html",
        "templates/datenschutz.html",
        "static/css/default.css",
        "static/robots.txt",
        "static/sitemap.xml",
        "static/css/gridjs.css",
        "static/scss/_custom.scss",
        "static/scss/_variables.scss",
        "static/favicon.ico",
    ],
)

filegroup(
    name = "similarbooksjs",
    srcs = ["static/js/utils.js", "static/js/scripts.js"],
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
    data = [":templates", ":similarbooksjs", ":profile_pics"],
    visibility = ["//app:__subpackages__"],
)

py_library(
        name = "similarbooks_config",
    srcs = [
        "config.py",
    ],
    visibility = ["//visibility:public"],
)
