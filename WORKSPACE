workspace(name = "similarbooks")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

######################
# PYTHON SUPPORT
######################
http_archive(
    name = "rules_python",
    sha256 = "c03246c11efd49266e8e41e12931090b613e12a59e6f55ba2efd29a7cb8b4258",
    strip_prefix = "rules_python-0.11.0",
    url = "https://github.com/bazelbuild/rules_python/archive/refs/tags/0.11.0.tar.gz",
)

load("@rules_python//python:pip.bzl", "pip_install")

pip_install(
    name = "py_deps",
    python_interpreter = "/usr/bin/python3",
    requirements = "//3rdparty:requirements.txt",
)
