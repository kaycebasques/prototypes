load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def _gmp_impl(ctx):
    ctx.download(
        url = [
            "https://snapshot.debian.org/archive/debian/20230101T000000Z/pool/main/g/gmp/libgmp-dev_6.2.1%2Bdfsg-1%2Bdeb11u1_amd64.deb",
            "http://ftp.debian.org/debian/pool/main/g/gmp/libgmp-dev_6.2.1+dfsg-1+deb11u1_amd64.deb",
        ],
        output = "gmp_dev.deb",
        sha256 = "500dc89f80630f821956b27eaac69765a0c3189a7b1a5892c84594a7bed5a99e",
    )
    ctx.download(
        url = [
            "https://snapshot.debian.org/archive/debian/20230101T000000Z/pool/main/g/gmp/libgmp10_6.2.1%2Bdfsg-1%2Bdeb11u1_amd64.deb",
            "http://ftp.debian.org/debian/pool/main/g/gmp/libgmp10_6.2.1+dfsg-1+deb11u1_amd64.deb",
        ],
        output = "gmp10.deb",
        sha256 = "fc117ccb084a98d25021f7e01e4dfedd414fa2118fdd1e27d2d801d7248aebbc",
    )

    ctx.execute(["sh", "-c", """
for deb in gmp_dev.deb gmp10.deb; do
    mkdir -p "tmp_$deb"
    (cd "tmp_$deb" && ar x "../$deb" && tar -xf data.tar.*)
done
mkdir -p lib include
cp -P tmp_gmp_dev.deb/usr/lib/*-linux-gnu/libgmp.* lib/ 2>/dev/null || true
cp -P tmp_gmp10.deb/usr/lib/*-linux-gnu/libgmp.so* lib/ 2>/dev/null || true
cp -P tmp_gmp_dev.deb/usr/include/*-linux-gnu/gmp.h include/ 2>/dev/null || cp -P tmp_gmp_dev.deb/usr/include/gmp.h include/ 2>/dev/null || true
rm -rf tmp_*.deb *.deb
"""])

    ctx.file("BUILD.bazel", """
cc_library(
    name = "gmp",
    srcs = glob(["lib/libgmp.so*"], allow_empty = True) + glob(["lib/libgmp.a"], allow_empty = True),
    hdrs = glob(["include/*.h"], allow_empty = True),
    includes = ["include"],
    visibility = ["//visibility:public"],
)
""")

gmp_repository = repository_rule(implementation = _gmp_impl)

def _non_module_deps_impl(_mctx):
    http_archive(
        name = "zlib.dev",
        build_file = "//:zlib.BUILD.bazel",
        sha256 = "b5b06d60ce49c8ba700e0ba517fa07de80b5d4628a037f4be8ad16955be7a7c0",
        strip_prefix = "zlib-1.3",
        urls = ["https://github.com/madler/zlib/archive/v1.3.tar.gz"],
    )
    gmp_repository(name = "gmp")

non_module_deps = module_extension(implementation = _non_module_deps_impl)
