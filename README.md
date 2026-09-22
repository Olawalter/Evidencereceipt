<p align="center"><img src="docs/assets/evidence-receipt-mark.svg" width="140" alt="EvidenceReceipt"/></p>

# EvidenceReceipt - Turn Public Claims into Verifiable Evidence Receipts

**A standalone GenLayer Intelligent Contract that records whether a declared public source contains sufficient evidence to support a declared claim under a declared, versioned verification policy - retrieved and read independently by every validator, and stored as a structured receipt other contracts and agents can rely on.**

EvidenceReceipt does not decide whether a claim is true. It answers a narrower question that can be checked:

> Under this policy - what evidence is expected, which claim components it must establish, what counts as sufficient - does this source, as retrieved now, contain that evidence?

A policy owner fixes a verification policy: the kind of source expected (a certifier's register, a regulator's public register, a provider's official documentation), the claim components that must be established (entity, credential, scope, status, version...), what sufficient and insufficient support look like, the minimum support level, an optional freshness rule and optional authority domains. A requester asks one claim of one URL under that policy, committing to its hash. One consensus round has every validator retrieve the URL itself, derive the source status from the HTTP response, normalise the content and digest it, scan it in code for text addressed to the verifier, and only then ask the panel what it cannot compute: is this the kind of source the policy expects, is each component stated, implied, absent, contradicted or unclear, and what date does the source give. Every finding that bears on the claim quotes the source, re-grounded by each validator in the bytes it retrieved. Code derives the support level and the final result.

No model output ever reaches a support level, a final result or a date calculation.

Deployment of record: [`0x3482865cce66361bc356A0ea6F79EA7Fd3653664`](https://explorer-studio.genlayer.com/address/0x3482865cce66361bc356A0ea6F79EA7Fd3653664) on GenLayer StudioNet (chain 61999), from commit `82a3bd7`, byte-identical to `contracts/evidence_receipt.py`.

## At a glance

| Question | Answer |
|---|---|
| What is EvidenceReceipt | A reusable contract primitive: immutable versioned verification policies, bounded requests, one consensus verification each, an optional recheck, finality, re-verification with preserved history, and compact read methods. No frontend, backend, database or operator. |
| Who calls it | Agents and systems that must rely on a claim someone else made - "this API supports feature X", "this company holds certification Y", "this firm is licensed" - and any contract that gates an action on a final receipt. |
| Why a normal contract cannot do it | A deterministic contract can store a URL, a hash or a boolean someone supplied. It cannot retrieve an arbitrary public page and decide whether its contents establish a natural-language claim component by component. |
| Why GenLayer must do it | The decision is semantic and depends on live web content. A single operator's model would be an authority nobody can check; GenLayer has every validator retrieve and read the source independently, and stores only the reading they agree on. |
| What validators compare | The source status, the HTTP status, truncation, where text addressed to the verifier appears, and - for a STABLE source - the byte count, the normalised content digest, the raw hash, the title and the content type; then the final result, support level, reason, provenance, the required components when the outcome rests on all of them (with evidence found), and the freshness outcome when it decides. |
| What validators do not compare | Notes, quote choice and, for a DYNAMIC source, incidental content differences. Every quote is still re-grounded in each validator's own retrieval, and the receipt stores nothing the validators did not agree on. |
| What tests prove it | 206 Direct Mode tests across every source status, support level and reason code, hostile sources, forged leader receipts through the captured validator, freshness and the lifecycle; a 75-of-75 mutation sweep; GenVM lint; a live diagnostic pass, a fresh-reader audit and a 78-transaction live run on StudioNet. See "Verified". |

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

| Check | Result |
|---|---|
| `python -m pytest tests/direct -q` | 206 passed |
| `genvm-lint check contracts/evidence_receipt.py --json` | lint ok, validation ok, 25 methods (17 view, 8 write); one I200 notice that a newer runner exists |
| `ruff check .` | clean |
| `python scripts/generate_fixtures.py --check` | fixtures match (24 files) |
| `python scripts/mutation_check.py --jobs 3` | on the deployed contract: 75 of 75 mutations killed (`deploy/mutation_sweep_final.txt`); earlier sweeps and the survivors that led to new tests are in `deploy/mutation_sweep.txt` and `deploy/mutation_recheck.txt` |
| `python scripts/deploy_studionet.py --verify` | byte-identical, 25 schema methods |
| `python -m pytest tests/integration -q` | 6 passed, 1 skipped (the opt-in live write) |
| CI (`.github/workflows/ci.yml`) | green on every pushed commit |
| Clean clone | CLEAN_CLONE_PENDING |
| `python scripts/preflight.py` | every check passes |

The live run of record on `0x3482865cce66361bc356A0ea6F79EA7Fd3653664`: 78 transactions from 2026-09-22T10:32:48Z to 2026-09-22T12:33:27Z, none of them a rejected round (`deploy/live_run_transcript.json`, `deploy/live_run.log`). Sources were served from `https://raw.githubusercontent.com/Olawalter/Evidencereceipt/de4dda6/fixtures/` and read as STABLE, except `CE01:dynamic`, the same source read as DYNAMIC.

| Case | Expected | Observed | Decided by | Held |
|---|---|---|---|---|
| [CE01](https://explorer-studio.genlayer.com/tx/0xa14d420836c5c749c0a68a06cceb75be027d4a21b3ed91aa66a11716c93426dc) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [CE01:dynamic](https://explorer-studio.genlayer.com/tx/0x72e15c1c2bfb5e228ec272a42d6aeeabcc00cb7ec87355902701924873266f60) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [CE01:v2](https://explorer-studio.genlayer.com/tx/0x48961102dcc37b58b1e1cb1c44bba940afdf184ace5ab5bf7c57cc64d9f71332) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [CE02](https://explorer-studio.genlayer.com/tx/0x88f6335765e7b5a35d32eb39b634d636d548a38cd1559d368169480d58096b56) | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | PANEL | yes |
| [CE03](https://explorer-studio.genlayer.com/tx/0xbb506620cd962c36282879cbe45e54c7da8470113a95e93407dfec750b1c1c8a) | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | PANEL | yes |
| [CE04](https://explorer-studio.genlayer.com/tx/0xf3f46b4097a92a68c59fbb8388f8dda09e2a2efb04ae20a50685c3a16863b58b) | NOT_SUPPORTED / INSUFFICIENT / WRONG_SOURCE_TYPE | NOT_SUPPORTED / INSUFFICIENT / WRONG_SOURCE_TYPE | PANEL | yes |
| [LI01](https://explorer-studio.genlayer.com/tx/0xad7a1f22d73b5073eceeda4fd9c0ccb385679e910d12cb18a613c2be38570583) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [LI02](https://explorer-studio.genlayer.com/tx/0xcf1a7ba904a7ab22a08bd0ca887c5d384cef57e5806db1f49af3f3df913836c6) | INCONCLUSIVE / INSUFFICIENT / EVIDENCE_STALE | INCONCLUSIVE / INSUFFICIENT / EVIDENCE_STALE | PANEL | yes |
| [LI03](https://explorer-studio.genlayer.com/tx/0xfe3793ea2889fabb02694076cddfc17a40cfe67b4c2b372ae3094c90b4c327bc) | PARTIALLY_SUPPORTED / PARTIAL / COMPONENTS_MISSING | PARTIALLY_SUPPORTED / PARTIAL / COMPONENTS_MISSING | PANEL | yes |
| [LI04](https://explorer-studio.genlayer.com/tx/0x5c47b60e6f020e7e36a37efda98f6ee97cd8f9b329b5b6bf1d43385cf6e98201) | UNAVAILABLE / UNAVAILABLE / SOURCE_NOT_FOUND | UNAVAILABLE / UNAVAILABLE / SOURCE_NOT_FOUND | CODE | yes |
| [LI04:recheck](https://explorer-studio.genlayer.com/tx/0x78132730c5f89118de2104c21f1688b5a7c6202631f4eae9afaf622f11c78152) | UNAVAILABLE / UNAVAILABLE / SOURCE_NOT_FOUND | UNAVAILABLE / UNAVAILABLE / SOURCE_NOT_FOUND | CODE | yes |
| [AP01](https://explorer-studio.genlayer.com/tx/0x977f300930d8e8d462d50b2bf4113e9d24af0293fef9820e1230c118715ed8f0) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [AP02](https://explorer-studio.genlayer.com/tx/0x9f56b61c2e857d15a152ee77e16dafa3e5c7c37ecaf7807c90f9639e2dcc9dcb) | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | PANEL | yes |
| [AP03](https://explorer-studio.genlayer.com/tx/0xe2b5e577e67cbfafc674a0b63bdd46accb5f7330cd5b0cf05da4d52bdbb640f5) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [AP04](https://explorer-studio.genlayer.com/tx/0xd13e6d6ba40b811d467d2dc79b0f54a1dfffc4474b3c22d8409142669a582957) | SUPPORTED / STRONG / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | **no** |
| [AD01](https://explorer-studio.genlayer.com/tx/0xce6c928436b9c719515ffb6df4bc3d30266653de23a8631d9091fcbce54b4195) | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | CODE | yes |
| [AD02](https://explorer-studio.genlayer.com/tx/0xe4e53b395914fcd833466f0ab645e2379a564928a441bf59925326353bd74e07) | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | CODE | yes |
| [AD03](https://explorer-studio.genlayer.com/tx/0xb404031cee6c71b14d823ce8d1a37cb752a6c14b2469a74e12eac40131499933) | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | CODE | yes |
| [AD04](https://explorer-studio.genlayer.com/tx/0x738110a7a327f46e5688451c176455255f76e9782cf59d7b41b64032f95f5e15) | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | CODE | yes |
| [AD05](https://explorer-studio.genlayer.com/tx/0xe781ee7e9211150ea0cef8a43f8dc7ea29b7fe8f5e51f5d1c2e98f8b8deed714) | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | INCONCLUSIVE / INCONCLUSIVE / SOURCE_ADDRESSES_VERIFIER | CODE | yes |
| [AD06](https://explorer-studio.genlayer.com/tx/0x0ff2c21d007247b76e2a0f5c29e8f6542729b6b81142ee17530bcef3e4787383) | SUPPORTED / DIRECT / SUPPORT_MET | SUPPORTED / DIRECT / SUPPORT_MET | PANEL | yes |
| [AD07](https://explorer-studio.genlayer.com/tx/0x4f73644cf9c426baf46a50f9a72b9038204a97424744d088e464a061ef83ba2d) | NOT_SUPPORTED / INSUFFICIENT / WRONG_SOURCE_TYPE | NOT_SUPPORTED / INSUFFICIENT / WRONG_SOURCE_TYPE | PANEL | yes |
| [AD08](https://explorer-studio.genlayer.com/tx/0x96b79ad6626f2f4f29a0873894059d67c74b3775b439a4012243e185c7f2c394) | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | CONTRADICTED / CONTRADICTED / COMPONENT_CONTRADICTED | PANEL | yes |

22 of 23 outcomes held; every code-decided outcome held. The one that did not: AP04 was expected SUPPORTED / STRONG (implied support) and read SUPPORTED / DIRECT - validators read "a repeated key returns the original response" as stating outright that a retry is safe, the same reading the diagnostic pass recorded twice. The final result was right; whether evidence is explicit or implied is a judgement models make differently, and the STRONG path is pinned by the Direct Mode suite.

| What | Result |
|---|---|
| Injection caught in code on real retrieval | HTML body, JSON field, title, hidden attribute, Markdown (AD01-AD05): panel never asked |
| Unavailable, never negative | LI04's source answered a real 404: `UNAVAILABLE` / `SOURCE_NOT_FOUND` |
| Recheck | LI04 [rechecked](https://explorer-studio.genlayer.com/tx/0x78132730c5f89118de2104c21f1688b5a7c6202631f4eae9afaf622f11c78152) once inside its window; the replaced receipt reads `SUPERSEDED_BY_RECHECK`; a [second recheck](https://explorer-studio.genlayer.com/tx/0x9d237aa970aad000781168c26362fa4bda02f18a01d0c42dffbc3c9b0e147893) was refused |
| DYNAMIC source | [CE01 read as DYNAMIC](https://explorer-studio.genlayer.com/tx/0x72e15c1c2bfb5e228ec272a42d6aeeabcc00cb7ec87355902701924873266f60): SUPPORTED, no digest stored |
| Finalization | every request finalized after its recheck window; `get_latest_receipt` returns each |
| Re-verification | CE01 [re-opened](https://explorer-studio.genlayer.com/tx/0xc70023f5917cb7cbc37aa9f1f7e39a43a55c8c1f4a4a1e08e8358003e9871c42) and [verified again](https://explorer-studio.genlayer.com/tx/0x48961102dcc37b58b1e1cb1c44bba940afdf184ace5ab5bf7c57cc64d9f71332): version 2, SUPPORTED, the same content digest as version 1 (the same pinned bytes); both versions FINALIZED in `get_history` |
| Refusals | 8 sent as real transactions, each refused with its sentence: a stranger verifying, a second verification, a duplicate request, an invalid policy version, a private-network URL, a non-https URL, a stranger retiring a policy, a second recheck |

Stated plainly: the run was resumed three times after faults in the run script, never in the contract. The finalize-inside-window refusal was first sent to CE02 after its window had closed, so the contract finalized it correctly; that transaction is kept under its true name (`finalize:CE02`), and when the refusals re-ran no request had an open window, so that refusal is covered by the Direct Mode suite only. The recheck step and the second finalization of CE01 then needed fixes for resuming; neither resent a transaction. An earlier deployment, `0x304678dc938eb0c0b3FC98026422ca4f89f0fBc1`, was superseded when its live run stopped at AD08 (`docs/CONSENSUS.md`).

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
