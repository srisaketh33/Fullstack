FROM eclipse-temurin:17-jre

ENV KAFKA_VERSION=3.7.0 \
    SCALA_VERSION=2.13 \
    KAFKA_HOME=/opt/kafka

RUN apt-get update && apt-get install -y curl bash && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz -o /tmp/kafka.tgz \
    && mkdir -p ${KAFKA_HOME} \
    && tar -xzf /tmp/kafka.tgz -C /opt \
    && mv /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} ${KAFKA_HOME} \
    && rm /tmp/kafka.tgz

COPY docker/kafka/server.properties ${KAFKA_HOME}/config/server.properties
COPY docker/kafka/entrypoint.sh /entrypoint.sh

RUN mkdir -p /var/lib/kafka && chmod +x /entrypoint.sh

EXPOSE 9092 29093

ENV KAFKA_CLUSTER_ID=MkU3OEVBNTcwNTJENDM2Qk

ENTRYPOINT ["/entrypoint.sh"]

