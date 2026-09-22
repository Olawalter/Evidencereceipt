# Ledgerly API reference - v2.3

Official documentation for the Ledgerly payments API.

## Idempotent requests

Send an `Idempotency-Key` header with any POST request. If a request with the same key
arrives again within 24 hours, Ledgerly does not repeat the operation: it returns the
response of the original request.
