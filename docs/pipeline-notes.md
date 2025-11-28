# Woodpecker pipeline notes

Expected repo layout for the template:
- `app/` or `src/`: Python code (FastAPI/RAG or similar) with `pyproject.toml` or `requirements.txt`.
- `infra/terraform`: Terraform modules/state.
- `infra/helm`: Helm chart (rooted at `chart/` inside this folder).

Configure the following Woodpecker secrets in the UI:
- `registry_url`, `registry_username`, `registry_password` for container pushes.
- `vault_addr`, `vault_token` if you use the Vault step (omit the step if unused).
- `aws_access_key_id`, `aws_secret_access_key` for Terraform.
- `kubeconfig` for Helm deploys (raw or base64 content).

Useful env vars the pipeline already uses:
- `CI_COMMIT_SHA` is provided by Woodpecker; defaults to `latest` if missing.
- `WOODPECKER_AGENT_SECRET` must match between server and agents (from `.env`).

Runbook:
1) Push/PR runs lint/tests, optional Vault fetch, and image build/push.
2) Push runs `terraform plan` for visibility; tags run Terraform apply + Helm deploy.
3) Adjust `depends_on` and `when` clauses for your promotion model (e.g., branch-based namespaces).
