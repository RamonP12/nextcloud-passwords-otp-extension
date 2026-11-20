# Linux/amd64 manifests of the official Node and Python images.
FROM docker.io/library/node:24.22.3-bookworm@sha256:aca79828f8a4afc627f189387c965625bcc419233946210a3b9522d90a59b5c6 AS node
FROM docker.io/library/python:3.12.14-bookworm@sha256:c90be507635af19768837aa7eeb2f4ce89a74d62962a335497b9df8edfb7f19d

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && test "$(node --version)" = v24.22.3 \
    && test "$(npm --version)" = 11.19.1

# Match the classic zlib compression format across hosts. Verify the upstream
# source before compilation and avoid an unpinned apt upgrade.
RUN set -eu; \
    cd /tmp; \
    curl -fsSLo zlib.tar.gz https://zlib.net/fossils/zlib-1.4.tar.gz; \
    echo '02dd159783677a749c04adbdd02b55b8a2bcc7e054f51b76b549199a916ad584  zlib.tar.gz' | sha256sum -c -; \
    tar -xzf zlib.tar.gz; \
    cd zlib-1.4; \
    ./configure --prefix=/opt/otp-zlib --shared; \
    make -j2; \
    make install; \
    cd /tmp; \
    rm -rf zlib.tar.gz zlib-1.4

ENV LD_LIBRARY_PATH=/opt/otp-zlib/lib \
    TZ=UTC \
    LC_ALL=C.UTF-8
RUN python3 -c 'import sys, zlib; assert sys.version_info[:3] == (3, 12, 14); assert zlib.ZLIB_RUNTIME_VERSION == "1.4"'
