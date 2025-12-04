#!/bin/bash
set -euo pipefail

export KAFKA_HOME=${KAFKA_HOME:-/opt/kafka}
export KAFKA_CLUSTER_ID=${KAFKA_CLUSTER_ID:-MkU3OEVBNTcwNTJENDM2Qk}

if [ ! -f "/var/lib/kafka/meta.properties" ]; then
  "$KAFKA_HOME/bin/kafka-storage.sh" format -t "$KAFKA_CLUSTER_ID" -c "$KAFKA_HOME/config/server.properties"
fi

exec "$KAFKA_HOME/bin/kafka-server-start.sh" "$KAFKA_HOME/config/server.properties"

