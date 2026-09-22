# Decision record

Why this contract, why this shape, and why GenLayer.

## The problem

Agents increasingly act on claims other agents make: this API supports
feature X, this company holds certification Y, this firm is licensed for
service Z. A deterministic contract can store the claim, a URL, a hash, a
timestamp or a boolean someone supplied. It cannot retrieve the source and
decide whether what it says is sufficient evidence for the claim. The precise
problem is not "is this true?" but "what evidence is sufficient to support
this claim under a declared policy, and does this source contain it?"

## Why this is a GenLayer-native problem

The decision needs live web retrieval and semantic reading - which
organisation a register names, whether a scope covers an activity, whether a
feature is current or only planned - and it must be reproducible by parties
who do not trust each other. GenLayer gives both: every validator retrieves the
source itself and reads it with its own model, and only the reading a majority
agrees on becomes state.

## The delete-GenLayer test

> Can a conventional deterministic smart contract independently retrieve an
> arbitrary public source and determine whether its contents provide
> sufficient semantic evidence for a natural-language claim under an explicit
> evidence policy?

No. Remove the consensus round and what remains: policies, hashes, URL
admission, duplicate checks, windows, receipts and history still work, and
code can still see an HTTP status and a digest. Nothing can say whether the
page is the right kind of source or whether it establishes each claim
component. The contract would reduce to storing a URL and an HTTP 200 - which
the brief names as drift.

## Alternative architectures

| Architecture | Why not |
|---|---|
| A centralised verification API that signs results | one operator's model and one operator's fetch are an authority nobody can check; a compromised or mistaken operator signs anything |
| A price-oracle-style network reporting a boolean | oracles agree on numbers from APIs, not on whether prose establishes each component of a claim under a written policy |
| A deterministic contract matching a keyword on the page | "certified" appears on marketing pages, expired entries and other companies' certificates; keyword matching fails exactly the cases that matter (CE02, CE03, CE04, AD08) |
| A human attestation registry | slow, subjective, and again a trusted party |
| EvidenceReceipt | the policy fixes the standard; validators each retrieve and read; code derives the result; receipts are immutable and consumable |

## Portfolio collision analysis

Two earlier builds in this portfolio are neighbours; the user chose to
differentiate.

| | Gazette | FactMesh | EvidenceReceipt |
|---|---|---|---|
| The question | what did this page say, and has it changed since | is this internet claim true, from evidence an off-chain engine found | does this declared source contain the evidence this declared policy requires for this claim |
| Evidence | one URL, attested as-is | many sources discovered off chain | one declared source, retrieved by every validator |
| Standard | none: a faithful record of the page | the adjudicator's judgement of truth | a versioned policy: expected source, required components, sufficiency, minimum support, freshness, authority domains |
| Output | a page attestation, edit and removal detection | a verdict on a claim | a receipt: source status, digest, per-component states, support level, final result |
| What it refuses to claim | what the page means | - | that the claim is true in the world |

Shared engineering is deliberate reuse proven on StudioNet: URL admission,
quote grounding by contiguous word runs, the structural gate, voting on leader
errors by prefix, and consensus on consequence.

## Ecosystem comparison

Centralised verification services (credential-checking APIs, trust badges) and
oracle networks exist; neither offers an open, policy-bound, per-component
reading of an arbitrary source that anyone can reproduce. Web-archiving
services record what a page said but not whether it supports a claim.

## The three-consumer proof

One primitive - claim, declared policy, source, verification, receipt - serves:

1. AI agent commerce: an agent relies on a capability only with a finalized
   receipt under an API-capability policy (AP01-AP04).
2. Credential and certification checks: a system admits a supplier only when
   the certifier's register establishes certification, scope and validity
   (CE01-CE04), or a regulator's register an active licence (LI01-LI04).
3. Protocol and API capability verification: a registry records capabilities
   from receipts and re-verifies when documentation changes.

[`docs/INTEGRATION.md`](docs/INTEGRATION.md) shows each consumer's read.

## Hardest technical risk

Agreement on live content. Two validators can retrieve different bytes from the
same URL - counters, banners, a deploy between requests. The design separates
what must be identical from what may differ: normalisation removes incidental
markup before digesting; a requester declares a source STABLE (digest compared)
or DYNAMIC (digest recorded, decision fields compared, every quote re-grounded
in each validator's own retrieval). The second risk is honest model variance on
components; the comparison is kept to what changes the result, and the live
diagnostic pass on a disposable deployment is where it is measured
([`docs/CONSENSUS.md`](docs/CONSENSUS.md)).

## Why a standalone Intelligent Contract

The policy, the request, the retrieval, the reading and the receipt must live
in one place no party controls. Split across a backend and a registry
contract, the backend becomes the verifier. As one contract, every receipt is
reproducible from its policy, its URL and its retrieval, and any contract or
agent can consume it.
