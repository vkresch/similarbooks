load("@rules_python//python:defs.bzl", "py_test")
load("@py_deps//:requirements.bzl", "requirement")

def pytest_test(name, srcs, deps = [], args = [], data = [], **kwargs):
    """
        Call pytest
    """
    py_test(
        name = name,
        srcs = [
            "//tools/pytest:pytest_wrapper.py",
        ] + srcs,
        main = "//tools/pytest:pytest_wrapper.py",
        args = args + ["$(location :%s)" % x for x in srcs],
        deps = deps + [
            requirement("pytest"),
        ],
        **kwargs
    )
