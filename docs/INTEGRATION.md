# Integration

One receipt shape, three consumers. A consumer never re-verifies a claim: it
reads a finalized receipt and applies its own rule.

## The rule every consumer applies

```text
r = get_latest_receipt(request_id)
r["found"] and r["state"] == "FINALIZED" and r["final_result"] == "SUPPORTED"
```

`get_latest_receipt` returns only a finalized receipt: one still inside its
recheck window is not returned. A consumer that trusts a specific policy also
checks `r["policy_id"]` and `r["policy_hash"]`, and may require
`r["support_level"] == "DIRECT"` when implied support is not enough, or check
`r["retrieval_timestamp"]` for its own freshness rule. `record_digest` lets it
pin exactly which receipt it acted on.

## Consumer 1 - AI agent commerce

An agent offers a service that relies on "the Ledgerly API sends signed
webhooks for settled payments". The buying agent requires a finalized receipt
under an API-capability policy it trusts before it relies on that capability.

```python
@gl.contract_interface
class EvidenceReceipt:
    class View:
        def get_latest_receipt(self, request_id: str) -> dict: ...

@gl.public.write
def accept_offer(self, offer_id: str, request_id: str) -> None:
    r = EvidenceReceipt(self.receipts).view().get_latest_receipt(request_id)
    if not (r["found"] and r["final_result"] == "SUPPORTED"):
        raise gl.vm.UserError("the capability is not evidenced")
    if r["policy_hash"] != self.trusted_api_policy:
        raise gl.vm.UserError("a policy this agent does not trust")
    self.accepted[offer_id] = r["verification_id"]
```

## Consumer 2 - credential and certification verification

A procurement system accepts a supplier only with a finalized receipt showing
the certifier's register establishes certification, scope and current
validity.

```python
@gl.public.write
def admit_supplier(self, supplier: str, request_id: str) -> None:
    r = EvidenceReceipt(self.receipts).view().get_latest_receipt(request_id)
    if not (r["found"] and r["final_result"] == "SUPPORTED"):
        raise gl.vm.UserError("certification not evidenced: " + r.get("reason_code", ""))
    scope = [c for c in r["components"] if c["component_id"] == "scope"][0]
    if scope["state"] != "EXPLICIT":
        raise gl.vm.UserError("the scope must be stated, not implied")
    self.suppliers[supplier] = r["record_digest"]
```

## Consumer 3 - protocol and API capability verification

An integration registry records which protocols support which features, using
receipts as evidence-backed inputs rather than the originating agent's word,
and re-verifies periodically because documentation changes.

```python
@gl.public.write
def record_capability(self, key: str, request_id: str) -> None:
    r = EvidenceReceipt(self.receipts).view().get_latest_receipt(request_id)
    if not r["found"]:
        raise gl.vm.UserError("no final receipt yet")
    self.capabilities[key] = {"result": r["final_result"],
                              "support": r["support_level"],
                              "as_of": r["retrieval_timestamp"],
                              "digest": r["content_digest"]}
```

When the registry's copy is older than it accepts, it calls
`request_reverification(request_id)` (as requester) and `verify`; the old
receipt stays in `get_history`.

These sketches show the read; each consumer adds its own storage and policy.

## Off-chain consumers

```python
client.read_contract(address=RECEIPTS, function_name="get_latest_receipt", args=[rid])
client.read_contract(address=RECEIPTS, function_name="get_history", args=[rid])
client.read_contract(address=RECEIPTS, function_name="get_result", args=[vid])
```
