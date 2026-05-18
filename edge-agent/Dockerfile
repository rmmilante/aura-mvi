FROM rust:1.75-slim as builder
WORKDIR /usr/src/app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /usr/src/app/target/release/edge-agent /usr/local/bin/
ENV SIMULATOR_URL=http://simulator:8001
ENV SIGNAL_API_URL=http://signal-api:8003
EXPOSE 8002
CMD ["edge-agent"]