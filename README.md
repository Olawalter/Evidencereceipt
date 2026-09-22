<p align="center"><img src="docs/assets/evidence-receipt-mark.svg" width="140" alt="EvidenceReceipt"/></p>

# EvidenceReceipt - Turn Public Claims into Verifiable Evidence Receipts

**A standalone GenLayer Intelligent Contract that records whether a declared public source contains sufficient evidence to support a declared claim under a declared, versioned verification policy - retrieved and read independently by every validator, and stored as a structured receipt other contracts and agents can rely on.**

EvidenceReceipt does not decide whether a claim is true. It answers a narrower question that can be checked:

> Under this policy - what evidence is expected, which claim components it must establish, what counts as sufficient - does this source, as retrieved now, contain that evidence?

A policy owner fixes a verification policy: the kind of source expected (a certifier's register, a regulator's public register, a provider's official documentation), the claim components that must be established (entity, credential, scope, status, version...), what sufficient and insufficient support look like, the minimum support level, an optional freshness rule and optional authority domains. A requester asks one claim of one URL under that policy, committing to its hash. One consensus round has every validator retrieve the URL itself, derive the source status from the HTTP response, normalise the content and digest it, scan it in code for text addressed to the verifier, and only then ask the panel what it cannot compute: is this the kind of source the policy expects, is each component stated, implied, absent, contradicted or unclear, and what date does the source give. Every finding that bears on the claim quotes the source, re-grounded by each validator in the bytes it retrieved. Code derives the support level and the final result.

No model output ever reaches a support level, a final result or a date calculation.

Deployment of record: [`0x304678dc938eb0c0b3FC98026422ca4f89f0fBc1`](https://explorer-studio.genlayer.com/address/0x304678dc938eb0c0b3FC98026422ca4f89f0fBc1) on GenLayer StudioNet (chain 61999), from commit `168192e`, byte-identical to `contracts/evidence_receipt.py`.

## At a glance

| Question | Answer |
|---|---|
| What is EvidenceReceipt | A reusable contract primitive: immutable versioned verification policies, bounded requests, one consensus verification each, an optional recheck, finality, re-verification with preserved history, and compact read methods. No frontend, backend, database or operator. |
| Who calls it | Agents and systems that must rely on a claim someone else made - "this API supports feature X", "this company holds certification Y", "this firm is licensed" - and any contract that gates an action on a final receipt. |
| Why a normal contract cannot do it | A deterministic contract can store a URL, a hash or a boolean someone supplied. It cannot retrieve an arbitrary public page and decide whether its contents establish a natural-language claim component by component. |
| Why GenLayer must do it | The decision is semantic and depends on live web content. A single operator's model would be an authority nobody can check; GenLayer has every validator retrieve and read the source independently, and stores only the reading they agree on. |
| What validators compare | The source status, the HTTP status, truncation, where text addressed to the verifier appears, and - for a STABLE source - the byte count, the normalised content digest, the raw hash, the title and the content type; then the final result, support level, reason, provenance, the required components when the outcome rests on all of them (with evidence found), and the freshness outcome when it decides. |
| What validators do not compare | Notes, quote choice and, for a DYNAMIC source, incidental content differences. Every quote is still re-grounded in each validator's own retrieval, and the receipt stores nothing the validators did not agree on. |
| What tests prove it | VERIFIED_PENDING |

## The receipt model

```text
claim --> declared evidence policy --> source --> verification --> receipt
```

| Field | Meaning |
|---|---|
| `claim`, `claim_context` | what was asked, bounded |
| `source_url`, `final_url`, `source_domain` | where it was asked of; the contract does not follow redirects (a redirect is `REDIRECTED`), so the final URL is the source URL |
| `source_status`, `http_status` | `RETRIEVED`, `PARTIAL`, `REDIRECTED`, `NOT_FOUND`, `FORBIDDEN`, `SERVER_ERROR`, `TIMEOUT`, `INVALID_CONTENT`, `UNSUPPORTED_CONTENT` |
| `content_digest`, `source.raw_sha256`, `source.byte_count` | for a STABLE source, the sha256 of the normalised text and of the raw bytes observed at `retrieval_timestamp`, agreed by every validator - an identity for what was read, not a proof that the site will not change; empty for a DYNAMIC source |
| `source_shape` | whether the source is the kind the policy expects, with the quote that shows it |
| `components`, `components_decisive` | each claim component's state (`EXPLICIT`, `IMPLIED`, `ABSENT`, `CONTRADICTED`, `UNCLEAR`), its quotes and whether validators `compared` it - compared when the outcome rests on every required component; under a contradiction the contradicted readings are kept uncompared; empty when an earlier reason decided the outcome |
| `freshness` | required or not, the date the source states, and `CURRENT`, `STALE` or `UNDATED` as code computed it |
| `evidence_found`, `support_level`, `final_result`, `reason_code` | the outcome |
| `relevant_excerpt` | the decisive passages, bounded to 400 characters |
| `policy_id`, `policy_version`, `policy_hash`, `request_commitment` | which policy and which request produced it |
| `version`, `mode`, `recheck_of`, `record_digest` | where the receipt sits in the request's history |

Support levels: `DIRECT`, `STRONG`, `PARTIAL`, `INSUFFICIENT`, `CONTRADICTED`, `UNAVAILABLE`, `INCONCLUSIVE`. Final results: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_SUPPORTED`, `CONTRADICTED`, `UNAVAILABLE`, `INCONCLUSIVE`. The mapping and all 19 reason codes: [`docs/EVIDENCE_POLICY.md`](docs/EVIDENCE_POLICY.md).

## Deterministic and intelligent responsibilities

| Code decides | Consensus decides |
|---|---|
| identity, policy ownership, who may verify, recheck and re-verify | whether the source is the kind the policy expects |
| the immutable policy, its hash and the version a request commits to | each claim component: explicit, implied, absent, contradicted, unclear |
| field limits, URL admission, authority domains, duplicate requests | the date the source states for its evidence |
| source status from the HTTP response, normalisation, digests, truncation | |
| text addressed to the verifier (body, markup and attributes, title) | |
| freshness arithmetic, the support level, the final result | |
| receipts, finality, re-verification history, every state transition | |

## Lifecycle

```text
 policy     create_policy --> ACTIVE --retire_policy--> RETIRED (no new requests)

 request    request_verification (policy hash checked, window starts)
              |
              v
          CREATED --verify (consensus round)--> EVALUATED --recheck, once, in the window--> EVALUATED
              |                                     |                                    (new receipt,
              | window passes                       | window passes                       old one kept)
              v                                     v
       expire_request --> EXPIRED              finalize --> FINALIZED
                                                              |
                                                request_reverification
                                                              v
                                                     REVERIFY_REQUESTED --verify--> EVALUATED (version 2)
                                                              |
                                                window passes: expire_request --> FINALIZED (version 1 stands)
```

`VERIFYING` from the brief is not a stored state: a verification is one transaction, and a round that does not reach consensus stores nothing. A receipt is written once and never rewritten; a recheck or a re-verification adds a receipt, and `get_history` lists every one.

## Consumers

| Consumer | Asks | Relies on |
|---|---|---|
| AI agent commerce | "this API supports feature X" against the provider's documentation | `get_latest_receipt(request_id)`: `final_result == SUPPORTED` |
| Credential and certification checks | "company X holds certification Y" against the certifier's register | the same, with `components` for scope and validity |
| Protocol and API capability | "protocol X supports feature Y" against official documentation | the same, with `support_level` when implied support is not enough |

[`docs/INTEGRATION.md`](docs/INTEGRATION.md) shows each consumer's read.

## Contract

`contracts/evidence_receipt.py` - one file, 25 public methods (8 write, 17 view). No method is payable.

| Write | Who | Notes |
|---|---|---|
| `create_policy(policy_json)` | anyone (becomes owner) | fixed and hashed; a new version supersedes, never rewrites |
| `retire_policy(policy_id)` | owner | stops new requests |
| `request_verification(policy_id, policy_hash, claim, claim_context, source_url, content_stability)` | anyone | commits to the policy hash; duplicate and open-request limits |
| `verify(request_id)` | requester or policy owner | one consensus round |
| `recheck(request_id)` | requester or policy owner | once per verification event, inside the window; the replaced receipt is kept |
| `finalize(request_id)` | anyone | after the recheck window |
| `request_reverification(request_id)` | requester or policy owner | opens a new verification event on a finalized request |
| `expire_request(request_id)` | anyone | after an unused verification window |

| View | Returns |
|---|---|
| `get_receipt(verification_id)` | the full receipt and its state (`EVALUATED`, `FINALIZED`, `SUPERSEDED_BY_RECHECK`) |
| `get_claim`, `get_source`, `get_result`, `get_support_level`, `get_content_digest`, `get_policy_hash`, `get_verification_status` | one part of a receipt each |
| `get_latest_receipt(request_id)` | the most recent finalized receipt - what a consumer relies on |
| `get_request`, `get_history`, `get_actions` | a request, its receipts oldest first, and which action is open at a time |
| `get_policy`, `list_policies`, `list_requests`, `get_stats`, `get_config` | policies, pages of ids, totals, enums and limits |

## STABLE and DYNAMIC sources

A request declares how its source behaves. For a `STABLE` source - a commit-pinned file, a static register page - every validator must read identical normalised content: the digest and byte count are compared. For a `DYNAMIC` source - a page with counters or rotating banners - no digest can be agreed, so none is stored; agreement rests on the decision fields and on every quote being present in each validator's own retrieval. Normalisation removes markup, scripts, styles, comments and hidden characters before digesting, so incidental HTML never splits a STABLE round.

## Verified

LIVE_RUN_PENDING

## Repository

```text
contracts/evidence_receipt.py           the contract
tests/direct/                           Direct Mode suite (happy paths, hardening, adversarial)
tests/integration/                      checks against the StudioNet deployment
fixtures/                               policies, source documents, four case catalogues
scripts/generate_fixtures.py            writes fixtures/ (--check in CI)
scripts/make_wallets.py                 demo wallets: keys in .data/ (gitignored)
scripts/deploy_studionet.py             deploy, record, verify byte parity
scripts/live_run.py                     the diagnostic pass and the live run
scripts/mutation_check.py               mutation kill check over the contract's guards
scripts/preflight.py                    release gate: documents say only what is true
scripts/fetch_genvm_bundle.py           seeds the GenVM runner cache for the toolchain
deploy/                                 deployment record, live transcript, diagnostics
docs/                                   consensus, evidence policy, security, adversarial testing, integration, deployment
```

## Getting started

```bash
pip install -r requirements-test.txt
```

```bash
python scripts/fetch_genvm_bundle.py
```

```bash
python scripts/generate_fixtures.py --check
```

```bash
python -m pytest tests/direct -q
```

```bash
genvm-lint check contracts/evidence_receipt.py --json
```

```bash
python scripts/preflight.py
```

If other GenVM bundles are cached on the machine, pin the linter and the test runner with `GENVM_VERSION=v0.3.0-rc7`. A sample policy, claim, verification, receipt inspection, an unavailable source and an adversarial source all run in `tests/direct/test_evidence_receipt.py`; running them on StudioNet: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Security

Prompt injection in bodies, markup, titles, JSON and documentation; URL admission and its limits; redirects; dynamic content; digest limits; forged leaders; replay and duplicates; policy versioning and receipt immutability: [`docs/SECURITY.md`](docs/SECURITY.md) and [`docs/ADVERSARIAL_TESTING.md`](docs/ADVERSARIAL_TESTING.md).

## Limitations

- EvidenceReceipt does not prove universal truth. It records whether one source supports one claim under one policy at one retrieval.
- A content digest identifies what was read; it does not make a website immutable. A later verification that reads different content creates a new receipt.
- Source authority is judged from the source itself and, where the policy names them, its authority domains. A convincing fake on an allowed domain would pass; domain names are a signal, not proof.
- Only text is read: HTML, Markdown, JSON, XML and plain text, up to 12,000 normalised characters. Pages that need JavaScript to render their content read as `INVALID_CONTENT` or without the evidence.
- The contract does not follow redirects; a redirected source is `REDIRECTED`, and the requester can ask of the final URL instead.
- Consensus assumes an honest validator majority; models can misread a subtle claim, which the recheck and re-verification exist to revisit.
- Everything stored is public on chain.

## Not production-ready

This is a StudioNet deployment of an unaudited contract. A receipt is only as good as the policy that defines sufficient evidence.

## Licence

MIT - see [`LICENSE`](LICENSE).
