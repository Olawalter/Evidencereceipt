# Submission - EvidenceReceipt

**Turn public claims into verifiable evidence receipts.**

A standalone GenLayer Intelligent Contract that records whether a declared
public source contains sufficient evidence to support a declared claim under a
declared, versioned verification policy. Every validator retrieves and reads
the source itself; code derives the result; the receipt is immutable and
consumable by other contracts and agents. It does not prove universal truth.

**Repository** - https://github.com/Olawalter/Evidencereceipt

**StudioNet address** - `0x3482865cce66361bc356A0ea6F79EA7Fd3653664`

**Explorer** - https://explorer-studio.genlayer.com/address/0x3482865cce66361bc356A0ea6F79EA7Fd3653664

**Deployment transaction** - `0x5164d44efc2bf6a7cfdf6e111995bce0e8908abd7d020f169eeec8b27d7bc70e`, FINALIZED, leader execution SUCCESS, votes AGREE, AGREE, AGREE, IDLE, IDLE

**Signer** - `0x1d9bc5438Add9e713224051CE27BE620Fb1FFdE7`

**Deployed source** - `contracts/evidence_receipt.py` at commit `82a3bd7`, sha256 `8f05ac4880ded2cc7299c6bf4df4ce8e971a5208b7b8dca38f914548d5ed1bf7`, https://github.com/Olawalter/Evidencereceipt/blob/82a3bd72bae8e6e47ba55c58d77589b41392f7bc/contracts/evidence_receipt.py - byte-identical on chain (`gen_getContractCode`)

## Why GenLayer is required

Whether a certifier's register names the claimed organisation with a
certificate whose scope covers the claim and which is still valid, whether a
provider's documentation supports a feature in the current version or only
plans it, whether a regulator's page shows an active licence - these need live
retrieval and semantic reading that parties who do not trust each other can
reproduce. A deterministic contract can store a URL and an HTTP 200; a single
operator's model is an authority nobody can check. GenLayer has every validator
retrieve and read the source independently and stores only the reading they
agree on.

## What the contract does

- Policies: immutable and hashed - expected source, required claim components,
  sufficient and insufficient support, minimum support level, optional
  freshness and authority domains. A request commits to the policy hash.
- Verification: code derives the source status from the HTTP response,
  normalises and digests the content, and catches text addressed to the
  verifier in the body, markup or title; the panel judges the source type and
  each component (explicit, implied, absent, contradicted, unclear), quoting
  the source; code derives the support level and final result.
- STABLE sources: validators compare the content digest. DYNAMIC sources:
  decision fields compared, every quote re-grounded, no digest stored.
- One recheck before finality, permissionless finalization, re-verification
  that keeps every earlier receipt, and compact read methods.

## Test and validation results

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

## Live evidence

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

Before the deployment of record, a diagnostic pass on a disposable deployment and a fresh-reader audit changed the contract: receipt fields no validator compared are now compared or not stored; quotes must be one contiguous passage; markup is stripped in linear time; the marker scan undoes soft hyphens, split tags and numeric entities; component states are compared only when the outcome rests on them, and under a contradiction only the outcome is (`docs/CONSENSUS.md`).

## Known limitations

EvidenceReceipt records whether one source supports one claim under one policy
at one retrieval; it does not prove the claim true. A content digest identifies
what was read, not that the site will stay the same. Source authority is judged
from the source and, where named, its authority domains - a convincing fake on
an allowed domain would pass. Only text is read, up to 12,000 normalised
characters; pages that need JavaScript to render their content cannot be read.
The contract does not follow redirects. Whether evidence is explicit or only
implied is a judgement models make differently (see `docs/CONSENSUS.md`).
Unaudited; StudioNet is a test network.

## Reviewer fast path

```bash
python -m pytest tests/direct -q
```

```bash
python scripts/deploy_studionet.py --verify
```

Then read `docs/EVIDENCE_POLICY.md` (how a source becomes a receipt),
`docs/CONSENSUS.md` (what validators compare, and what the diagnostic pass and
the audit changed) and `docs/SECURITY.md`. The contract is one file,
`contracts/evidence_receipt.py`.

## Portal description

EvidenceReceipt turns public claims into verifiable evidence receipts on GenLayer. It does not ask AI whether a claim is true. A policy owner fixes what evidence is sufficient - the kind of source expected, the claim components it must establish, freshness and trusted domains - and anyone can ask whether one public page supports one claim under that policy. Every validator retrieves the page itself; code decides reachability, content identity and text aimed at the verifier; validators judge the source type and each component, quoting the page; code derives the support level and result. Receipts are immutable, with a recheck, finality and re-verification that keeps history. Live on StudioNet: 22 of 23 outcomes held, every injection caught, an unavailable source never read as negative.
