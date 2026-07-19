load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def _non_module_deps_impl(_mctx):
    http_archive(
        name = "zlib.dev",
        build_file = "//:zlib.BUILD.bazel",
        sha256 = "b5b06d60ce49c8ba700e0ba517fa07de80b5d4628a037f4be8ad16955be7a7c0",
        strip_prefix = "zlib-1.3",
        urls = ["https://github.com/madler/zlib/archive/v1.3.tar.gz"],
    )

non_module_deps = module_extension(implementation = _non_module_deps_impl)
