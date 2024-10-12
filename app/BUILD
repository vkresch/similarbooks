load("@py_deps//:requirements.bzl", "requirement")

py_library(
    name="flask_library",
    deps = [
        requirement("flask"),
        requirement("graphql-server"),
        requirement("flask_mongoengine"),
        requirement("flask_wtf"),
        requirement("flask_simple_captcha"),
        requirement("flask_caching"),
        requirement("email_validator"),
        requirement("passlib"),
        requirement("requests"),
    ],
)

py_library(
    name="similarbooks_library",
    deps = [
        "//app/similarbooks:similarbooks_lib",
        ":flask_library",
        "//spiders/bookspider:schemas",
    ],
)

py_binary(
    name = "similarbooks_local",
    main = "main.py",
    srcs = ["main.py"],
    python_version = "PY3",
    deps = [
        ":similarbooks_library",
    ],
)

py_binary(
    name = "similarbooks_wsgi",
    main = "wsgi.py",
    srcs = ["wsgi.py"],
    python_version = "PY3",
    deps = [
        requirement("gunicorn"),
        ":similarbooks_library",
    ],
)
