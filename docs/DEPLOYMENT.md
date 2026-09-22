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

DEPLOY_RECORD_PENDING
