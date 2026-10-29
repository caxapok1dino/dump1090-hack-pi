FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config librtlsdr-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY Makefile dump1090.c anet.c anet.h ./
RUN make

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ffmpeg hackrf librtlsdr0 python3 tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /src/dump1090 ./dump1090
COPY gmap.html ./gmap.html
COPY docker/start.sh docker/record.py ./docker/
RUN mkdir -p /recordings && chmod +x ./docker/start.sh

EXPOSE 8080 30002 30003
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/app/docker/start.sh"]
