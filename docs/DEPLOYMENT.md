# Deployment

The workflow, then only facts a receipt, a read or a command output shows.
Every recorded value is in `deploy/deployment.json`, written by
`scripts/deploy_studionet.py`.

## Assumptions

| Item | Value |
|---|---|
| Network | GenLayer StudioNet, chain id 61999, RPC `https://studio.genlayer.com/api`, explorer `https://explorer-studio.genlayer.com` |
| Gas | StudioNet is gasless; no method of this contract is payable |
| Wallets | the deployer key is created on first use in `.data/deployer.json`; the demo wallets' keys are in `.data/demo_wallets.json` (`scripts/make_wallets.py`); `.data/` is gitignored and no key is ever printed |
| Environment variables | none are required. `GENVM_VERSION=v0.3.0-rc7` pins the linter and the test runner when other GenVM bundles are cached; `EVIDENCE_RECEIPT_LIVE_WRITES=1` opts the integration suite into one write |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Sources | a live run serves `fixtures/sources/` from a commit-pinned `raw.githubusercontent.com` URL, so every validator retrieves exactly the committed bytes |

## Workflow

Build and validate (the contract is one Python file; there is no build step
beyond the checks):

```bash
pip install -r requirements-test.txt
```

```bash
python scripts/fetch_genvm_bundle.py
```

```bash
genvm-lint check contracts/evidence_receipt.py --json
```

```bash
python -m pytest tests/direct -q
```

Deploy and capture the address - the script refuses an uncommitted, non-ASCII
or CR-bearing contract, waits for FINALIZED, requires leader execution
SUCCESS, reads the deployed source back with `gen_getContractCode` and writes
`deploy/deployment.json` only after the byte comparison:

```bash
python scripts/deploy_studionet.py
```

Post-deployment check:

```bash
python scripts/deploy_studionet.py --verify
```

```bash
python -m pytest tests/integration -q
```

Sample policy, verification request, receipt inspection, unavailable and
adversarial sources, recheck and re-verification - the live run does all of
them with real transactions:

```bash
python scripts/live_run.py <address> --raw-base https://raw.githubusercontent.com/<owner>/<repo>/<commit>/fixtures/ --phase full
```

By hand, with any GenLayer client: `create_policy(policy_json)` with a policy
from `fixtures/policies.json`; `request_verification(policy_id, policy_hash,
claim, claim_context, source_url, "STABLE")`; `verify(request_id)`;
`get_receipt(verification_id)`; after the recheck window `finalize(request_id)`
and `get_latest_receipt(request_id)`; later `request_reverification(request_id)`
and `verify(request_id)` again, then `get_history(request_id)`.

## Deployment of record

| Item | Value |
|---|---|
| Network | GenLayer StudioNet, chain id 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | `0x3482865cce66361bc356A0ea6F79EA7Fd3653664` |
| Explorer | https://explorer-studio.genlayer.com/address/0x3482865cce66361bc356A0ea6F79EA7Fd3653664 |
| Deployment transaction | `0x5164d44efc2bf6a7cfdf6e111995bce0e8908abd7d020f169eeec8b27d7bc70e` |
| Deployed at | 2026-09-22T10:32:00Z |
| Receipt | status FINALIZED, leader execution SUCCESS, votes AGREE, AGREE, AGREE, IDLE, IDLE |
| Source commit | `82a3bd72bae8e6e47ba55c58d77589b41392f7bc` |
| Source blob | `0a134a438ad684db9478f5ffac46e2037c38e148` |
| Source sha256 | `8f05ac4880ded2cc7299c6bf4df4ce8e971a5208b7b8dca38f914548d5ed1bf7` |
| Deployed source sha256 (`gen_getContractCode`) | `8f05ac4880ded2cc7299c6bf4df4ce8e971a5208b7b8dca38f914548d5ed1bf7` - byte-identical |
| Deployer (public address) | `0x1d9bc5438Add9e713224051CE27BE620Fb1FFdE7` |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |

`python scripts/deploy_studionet.py --verify`: deployed and repository sha256 equal, byte-identical, 25 schema methods.

## Toolchain

| Tool | Version |
|---|---|
| Python | 3.12.2 |
| genlayer-py | 0.16.3 |
| genlayer-test (Direct Mode) | 0.29.2 |
| genvm-linter | 0.11.0, GenVM bundle v0.3.0-rc7 |

`genvm-lint check contracts/evidence_receipt.py --json`: lint ok (3 checks), validation ok, 25 methods (17 view, 8 write). One notice, I200: a newer py-genlayer runner (`1zr6nqk5...`) is available. The contract stays on the runner this repository has deployed and run live; the newer runner was not tested here.

## Disposable diagnostic deployment

| Address | Source commit | Purpose | Record |
|---|---|---|---|
| `0x0C001C39156FE013bcAb3681cA6fF782B9461421` | `e5f47a1` | diagnostic pass 1: every catalogue case verified once, per-node readings recorded; then the AP04 re-run | `deploy/diagnostics/deployment_0x0c001c39.json`, `cases_0x0c001c39.json`, `cases_0x0c001c39_ap04.json` |

It is never the deployment of record. What it showed and what changed in response, and the fresh-reader audit that followed (seven defects, all fixed before the deployment of record): [`CONSENSUS.md`](CONSENSUS.md#live-diagnostic-findings).

## Live run

LIVE_FACTS_PENDING
