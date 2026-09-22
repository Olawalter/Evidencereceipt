# Ledgerly API reference - v2.3

Official documentation for the Ledgerly payments API.

## Webhooks

Ledgerly sends a signed webhook for every settled payment. Each delivery carries a
`Ledgerly-Signature` header computed with your endpoint secret, so you can verify
that the event came from Ledgerly. Signed settlement webhooks are supported since v2.1.
