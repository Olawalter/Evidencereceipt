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

VERIFIED_TABLE_PENDING

## Live evidence

LIVE_EVIDENCE_PENDING

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
