# OSS CI/CD Local Solution

Local POC stack: Gitea + Woodpecker CI, fronted by Traefik (or Caddy if you prefer). Use `.env.example` to create your own `.env` before starting.

## Quick start (Traefik)
1. Copy `.env.example` to `.env` and fill values. Generate `WOODPECKER_AGENT_SECRET` via `openssl rand -hex 32`.
2. Run `docker compose up -d`.
3. Visit `http://gitea.localhost` and complete first-time setup.
4. In Gitea → User Settings → Applications → OAuth2, create an app with redirect `http://ci.localhost/authorize`; place the client ID/secret into `.env`.
5. Restart: `docker compose up -d`, then log into `http://ci.localhost` via Gitea and activate your repo.

## Caddy alternative
Use `Caddyfile.example` as the reverse proxy if you prefer Caddy over Traefik; swap Traefik service in `docker-compose.yml` for a Caddy service that mounts that file and exposes 80/443.

## Pipeline template
`.woodpecker.yml` contains a Dirama-style pipeline for Python lint/test, Docker build/push, Terraform plan/apply, and Helm deploy, with Vault and registry/K8s secrets expected as Woodpecker secrets.
