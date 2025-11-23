FROM golang:1.21 as builder
ARG SERVICE
WORKDIR /src
COPY . .
RUN go build -o /out/app ./services/${SERVICE}

FROM debian:bookworm-slim
ARG SERVICE
COPY --from=builder /out/app /usr/local/bin/app
ENTRYPOINT ["/usr/local/bin/app"]
