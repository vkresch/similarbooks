load("@py_deps//:requirements.bzl", "requirement")
load("//tools/pytest:defs.bzl", "pytest_test")

pytest_test(
    name = "test_process_documents",
    srcs = ["test_process_documents.py"],
    size="small",
    deps = [
        requirement("somoclu"),
        requirement("numpy"),
        requirement("tqdm"),
        requirement("pandas"),
        "//app/similarbooks/main:constants",
        "//som:utils",
    ],
)
