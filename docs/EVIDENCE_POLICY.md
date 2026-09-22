# Evidence policy

What a verification policy contains, how a source becomes a receipt, and every
support level, final result and reason code in the order the contract applies
them.

## The policy

`create_policy(policy_json)` takes exactly these keys; a missing or unknown key
is refused.

| Key | Type and bound |
|---|---|
| `name` | text, 80 characters |
| `claim_type` | `CERTIFICATION`, `LICENSE`, `API_CAPABILITY`, `PROTOCOL_CAPABILITY` or `OTHER` |
| `expected_evidence`, `expected_source`, `sufficient_support`, `insufficient_support` | text, 600 characters each; nothing addressed to the evaluator, no hidden characters |
| `components` | 1 to 6 `{component_id, description, required}`; at least one required; ids are lowercase identifiers that cannot shadow a built-in subject |
| `minimum_support_level` | `DIRECT` (every required component stated explicitly) or `STRONG` (implied support is enough) |
| `authority_domains` | up to 4 lowercase DNS names; when present, a request's source host must be one of them or a subdomain of one - checked in code |
| `freshness_required`, `max_age_seconds` | when required, the source's stated date must be at most this old (1 day to 10 years); otherwise 0 |
| `verification_window_seconds` | how long a request may wait for its verification (60 s to 30 days) |
| `finality_delay_seconds` | how long a receipt can be rechecked before it may be finalized |
| `policy_version`, `supersedes` | 1-1000; empty or the policy id this version replaces (same owner, higher version) |

The policy is stored as canonical JSON with its sha256 (`get_policy` returns the
stored and a recomputed hash). A request passes that hash to
`request_verification`; a different hash is refused as an invalid policy
version. Every receipt names the policy id, version and hash it was produced
under. A new policy never alters an old receipt.

## An example: the licence policy in the fixtures

Claim: "BrightPay Ltd holds an active electronic money licence to issue
electronic money."

- Expected evidence: a public regulator or licensing authority page identifying
  the company, the relevant licence, the service category and its current
  status.
- Sufficient support: the source identifies the claimed entity and licence and
  shows that the licence is currently active for the claimed service.
- Insufficient support: marketing copy, an unrelated directory, an old cached
  article, or a page that mentions the company without establishing the
  licence.
- Components, all required: `authority`, `entity`, `licence`,
  `service_scope`, `status`.
- Minimum support `DIRECT`; freshness required, at most 365 days.

The certification and API capability policies are in `fixtures/policies.json`.

## Claim decomposition

A positive result is never issued because one component appears on the page.
Each component is judged separately:

| State | Meaning | Must quote the source |
|---|---|---|
| `EXPLICIT` | stated in so many words | yes |
| `IMPLIED` | established without being stated outright | yes |
| `ABSENT` | not established | no |
| `CONTRADICTED` | the source states the opposite - expired, withdrawn, a different scope, only a future version, a different entity | yes |
| `UNCLEAR` | the source is ambiguous | no |

A component mentioned for a different entity, product or version does not
establish it for the claim. A quote is one contiguous passage of the source. A
finding whose required quote is missing, spliced with an ellipsis, or absent
from the retrieved text falls back to `UNCLEAR`.

## Source status

Derived in code from the HTTP response, before anything is read:

| Status | When |
|---|---|
| `RETRIEVED` | 2xx, a text content type (or none), decodable UTF-8, visible text present |
| `PARTIAL` | as `RETRIEVED`, but the body exceeded 200,000 bytes or the normalised text 12,000 characters; the first 12,000 characters are read |
| `REDIRECTED` | 3xx; the contract does not follow it |
| `NOT_FOUND` | 404, 410 |
| `FORBIDDEN` | 401, 403 |
| `SERVER_ERROR` | 5xx |
| `TIMEOUT` | no response at all |
| `INVALID_CONTENT` | another 4xx, an empty body, invalid UTF-8, or no visible text |
| `UNSUPPORTED_CONTENT` | a non-text content type (images, PDFs, archives) |

HTTP 200 never implies support: a retrieved source still has to be the right
kind of source and establish every required component.

## Provenance

Source existence, reachability, authority and support stay separate:
reachability is the source status; authority is `authority_domains` (code) and
`SOURCE_SHAPE` (the panel); support is the components. Domain reputation alone
is never proof.

## Freshness

When a policy requires freshness, the panel reports the date the source gives
for its evidence (`FRESHNESS` = `DATED` with the date, or `UNDATED`). The quote
must contain that date's year, month and day. Code then compares it with the
transaction time: older than `max_age_seconds` is `STALE`; a date in the future
cannot vouch for freshness and counts as `UNDATED`. Retrieval time, the date the
source states and the request's creation time are three different things, and
the receipt records the first two.

## Support levels and final results, in precedence order

| Reason code | Final result | Support level |
|---|---|---|
| `SOURCE_REDIRECTED`, `SOURCE_NOT_FOUND`, `SOURCE_FORBIDDEN`, `SOURCE_SERVER_ERROR`, `SOURCE_TIMEOUT`, `SOURCE_INVALID_CONTENT`, `SOURCE_UNSUPPORTED_CONTENT` | UNAVAILABLE | UNAVAILABLE |
| `SOURCE_ADDRESSES_VERIFIER` - the body, markup or title addresses the verifier | INCONCLUSIVE | INCONCLUSIVE |
| `MODEL_OUTPUT_INVALID` | INCONCLUSIVE | INCONCLUSIVE |
| `WRONG_SOURCE_TYPE` - the source is not the kind the policy expects | NOT_SUPPORTED | INSUFFICIENT |
| `SOURCE_TYPE_UNCLEAR` | INCONCLUSIVE | INSUFFICIENT |
| `COMPONENT_CONTRADICTED` - a required component is contradicted | CONTRADICTED | CONTRADICTED |
| `FRESHNESS_UNVERIFIABLE` - freshness required, no usable date | INCONCLUSIVE | INSUFFICIENT |
| `EVIDENCE_STALE` | INCONCLUSIVE | INSUFFICIENT |
| `COMPONENT_UNCLEAR` - a required component is unclear | INCONCLUSIVE | INSUFFICIENT |
| `EVIDENCE_ABSENT` - every required component absent | NOT_SUPPORTED | INSUFFICIENT |
| `COMPONENTS_MISSING` - some required components absent | PARTIALLY_SUPPORTED | PARTIAL |
| `BELOW_MINIMUM_SUPPORT` - all present, one implied, policy wants DIRECT | PARTIALLY_SUPPORTED | STRONG |
| `SUPPORT_MET` - all present | SUPPORTED | DIRECT (all explicit) or STRONG |

The first code-decided rows never ask the panel. An unavailable source is never
`NOT_SUPPORTED`; unclear or insufficient evidence is never `SUPPORTED`; a source
that addresses the verifier is never read as evidence. Optional components are
recorded and never decide.

## Re-verification

Sources change. On a finalized request, the requester or the policy owner may
open a new verification event under the same policy version. It produces a new
receipt with `version` 2; the first receipt keeps its state and content. If
the new event's window passes without a verification, the request returns to
`FINALIZED` with the last final receipt standing.

## Limitations of AI evaluation

Models can misjudge a subtle component, especially `IMPLIED` support. Policies
that name concrete components and concrete sources evaluate far more reliably
than policies that ask for judgement of quality. The contract applies the
policy; it does not decide what the policy should be.
