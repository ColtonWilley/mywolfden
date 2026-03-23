---
paths:
  - "repos/wolfmqtt/**"
  - "**/wolfmqtt/**"
---

# wolfMQTT Patterns

## Overview
wolfMQTT is an MQTT client implementation supporting MQTT v3.1.1 and v5.0, with optional TLS via wolfSSL.

## Common Issues

### TLS Connection to Cloud IoT
- AWS IoT Core: requires mutual TLS (client cert + key)
- Azure IoT Hub: supports SAS tokens or X.509 client certs
- Google Cloud IoT: JWT-based auth over TLS
- **Common mistake**: Not loading the correct CA bundle for the cloud provider

### QoS Handling
- QoS 0: fire-and-forget (no acknowledgment)
- QoS 1: at-least-once (PUBACK expected)
- QoS 2: exactly-once (PUBREC/PUBREL/PUBCOMP handshake)
- **Common issue**: Not handling PUBACK callback → messages appear lost

### Keep-Alive / Ping
- MQTT keep-alive: client must send PINGREQ within keep-alive interval
- wolfMQTT handles automatically in blocking mode
- Non-blocking: application must call `MqttClient_WaitMessage()` periodically
- **Common issue**: Keep-alive timeout → broker disconnects client

### Non-Blocking Mode
- Enable with `MqttClient_SetNonBlocking()`
- Must handle `MQTT_CODE_CONTINUE` return — call function again
- Typical pattern: poll in main loop, handle all return codes

### Build
- Requires wolfSSL for TLS: `--enable-tls` in wolfMQTT configure
- Without TLS: `--disable-tls` for plain MQTT
- `--with-wolfssl=/path/to/wolfssl` to specify wolfSSL installation
