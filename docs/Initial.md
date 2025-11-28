# OSS CI/CD local solution

Perfect use case for Woodpecker 🙂 Let’s put together:

 1. Where to read the “official” way (3.12.x)
 2. A Docker Compose stack: Gitea + Woodpecker + Traefik
 3. How it’d look with Caddy instead
 4. A “Dirama-style” .woodpecker.yml for Python + K8s + Helm + Terraform + Vault

⸻

1. Docs you’ll actually care about

Core Woodpecker docs (current 3.12.x):
 • Gitea forge integration: env vars, OAuth callback URL, notes about Gitea on the same Docker network, and ALLOWED_HOST_LIST for webhooks  ￼
 • Server config: reverse proxy, TLS, DB backends, Traefik & Caddy examples in one place  ￼
 • Docker-Compose install example: minimal server + agent with SQLite and gRPC port; adapt for Gitea instead of GitHub  ￼

Nice real-world references (Gitea + Woodpecker + Traefik):
 • Blog: “Deploy Gitea and Woodpecker CI with Docker Compose (Traefik as reverse proxy)” – Gitea + Woodpecker + Traefik on a home server  ￼
 • Mondo docs: “Woodpecker CI with Docker Compose and Traefik as reverse proxy” – very similar pattern, just more production-ish  ￼

These essentially describe exactly what you want: Gitea + Woodpecker + Traefik, all via Compose.

⸻

2. Docker Compose: Gitea + Woodpecker + Traefik

Below: a single docker-compose.yml for a POC setup:
 • Network: devnet shared by everything
 • Reverse proxy: Traefik (HTTP only in this example; you can add TLS/Let’s Encrypt later)
 • Gitea: exposed at <http://gitea.localhost>
 • Woodpecker: exposed at <http://ci.localhost> via Traefik
 • Woodpecker DB: embedded SQLite persisted via volume
 • Agent: uses host Docker via /var/run/docker.sock and same network as Gitea (as suggested in the docs)  ￼

Create a .env next to the compose file:

WOODPECKER_HOST=<http://ci.localhost>
GITEA_EXTERNAL_URL=<http://gitea.localhost>

WOODPECKER_AGENT_SECRET=change-me-openssl-rand
WOODPECKER_GITEA_CLIENT=your-oauth-client-id
WOODPECKER_GITEA_SECRET=your-oauth-client-secret

In Gitea, create an OAuth app with redirect URI:
<http://ci.localhost/authorize> (same scheme + host as WOODPECKER_HOST, path /authorize per docs).  ￼

Now the docker-compose.yml:

version: "3.9"

services:
  traefik:
    image: traefik:v3.1
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      # add TLS/ACME here later if you want
    ports:
      - "80:80"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
    networks:
      - devnet

  gitea:
    image: gitea/gitea:1.22
    container_name: gitea
    restart: always
    environment:
      - GITEA__server__ROOT_URL=${GITEA_EXTERNAL_URL}
      - GITEA__server__DOMAIN=gitea.localhost
      - GITEA__server__SSH_DOMAIN=gitea.localhost
      - GITEA__webhook__ALLOWED_HOST_LIST=external,loopback
    volumes:
      - gitea-data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.gitea.rule=Host(`gitea.localhost`)"
      - "traefik.http.routers.gitea.entrypoints=web"
      - "traefik.http.services.gitea.loadbalancer.server.port=3000"
    networks:
      - devnet

  woodpecker-server:
    image: woodpeckerci/woodpecker-server:v3
    container_name: woodpecker-server
    restart: always
    depends_on:
      - gitea
    environment:
      # General
      - WOODPECKER_OPEN=true
      - WOODPECKER_HOST=${WOODPECKER_HOST}
      - WOODPECKER_AGENT_SECRET=${WOODPECKER_AGENT_SECRET}
      # HTTP / gRPC addresses (inside container)
      - WOODPECKER_SERVER_ADDR=:8000
      - WOODPECKER_GRPC_ADDR=:9000
      # Gitea integration
      - WOODPECKER_GITEA=true
      - WOODPECKER_GITEA_URL=${GITEA_EXTERNAL_URL}
      - WOODPECKER_GITEA_CLIENT=${WOODPECKER_GITEA_CLIENT}
      - WOODPECKER_GITEA_SECRET=${WOODPECKER_GITEA_SECRET}
    volumes:
      - woodpecker-server-data:/var/lib/woodpecker/
    labels:
      - "traefik.enable=true"
      # Web UI / HTTP API
      - "traefik.http.routers.woodpecker.rule=Host(`ci.localhost`)"
      - "traefik.http.routers.woodpecker.entrypoints=web"
      - "traefik.http.services.woodpecker.loadbalancer.server.port=8000"
      # If you later want Traefik to front gRPC for remote agents:
      # - "traefik.http.services.woodpecker-grpc.loadbalancer.server.port=9000"
      # - "traefik.http.services.woodpecker-grpc.loadbalancer.server.scheme=h2c"
    networks:
      - devnet

  woodpecker-agent:
    image: woodpeckerci/woodpecker-agent:v3
    container_name: woodpecker-agent
    restart: always
    depends_on:
      - woodpecker-server
    environment:
      - WOODPECKER_SERVER=woodpecker-server:9000
      - WOODPECKER_AGENT_SECRET=${WOODPECKER_AGENT_SECRET}
      # Make agent use same Docker network as Gitea so clone URLs just work
      - WOODPECKER_BACKEND_DOCKER_NETWORK=devnet
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - devnet

networks:
  devnet:

volumes:
  gitea-data:
  woodpecker-server-data:

Workflow:

 1. Start stack: docker compose up -d
 2. Visit <http://gitea.localhost> → configure admin user & SSH/HTTP.
 3. In Gitea: User Settings → Applications → OAuth2, create app:
 • Name: Woodpecker
 • Redirect URI: <http://ci.localhost/authorize>
 4. Put client_id and client_secret into .env.
 5. Restart: docker compose up -d
 6. Visit <http://ci.localhost> → log in via Gitea → enable repo → add .woodpecker.yml.

This sticks very close to the official forge + docker-compose examples, just wired with Traefik.  ￼

⸻

3. If you prefer Caddy over Traefik

If you want Caddy instead (simpler config, automatic HTTPS), Woodpecker docs give a minimal Caddyfile example: one vhost for HTTP/UI, one for gRPC using h2c  ￼.

Skeleton:

# Web UI + HTTP API

ci.example.com {
  reverse_proxy woodpecker-server:8000
}

# gRPC for remote agents, if needed

ci-grpc.example.com {
  reverse_proxy h2c://woodpecker-server:9000
}

Then in docker-compose.yml you’d replace the Traefik service with Caddy, mount this Caddyfile, and expose 80/443. Woodpecker + Gitea services stay almost identical; only labels change (Caddy doesn’t use Docker labels by default unless you add a plugin).

So: Traefik = more label-driven & dynamic; Caddy = simpler config file, great for automatic TLS.

⸻

4. “Dirama standard” .woodpecker.yml (Python + K8s + Helm + Terraform + Vault)

Here’s a starting point for a monorepo-ish DevOps pipeline:
 • Step 1: Python lint & tests (your FastAPI/RAG app)
 • Step 2: (optional) Fetch secrets from Vault (pattern only)
 • Step 3: Build & push Docker image
 • Step 4: Terraform plan/apply (infra)
 • Step 5: Helm deploy to K8s (app)

You’d create Woodpecker repo secrets in the UI:
 • registry_url, registry_username, registry_password
 • vault_addr, vault_token (or a better auth method)
 • aws_access_key_id, aws_secret_access_key (if using AWS in Terraform)
 • kubeconfig (base64-encoded or raw; see what you prefer)

kind: pipeline
type: docker
name: dirama-devops-pipeline

steps:
  lint_and_test:
    image: python:3.12-slim
    pull: true
    commands:
      - pip install uv
      - uv sync --dev
      - pytest -q
    when:
      event:
        - push
        - pull_request

# Optional pattern: pull secrets from Vault into a shared volume

  fetch_secrets_from_vault:
    image: hashicorp/vault:1.17
    environment:
      VAULT_ADDR:
        from_secret: vault_addr
      VAULT_TOKEN:
        from_secret: vault_token
    volumes:
      - name: ci-secrets
        path: /secrets
    commands:
      - vault kv get -field=AWS_ACCESS_KEY_ID  secret/ci/project > /secrets/aws_access_key_id
      - vault kv get -field=AWS_SECRET_ACCESS_KEY secret/ci/project > /secrets/aws_secret_access_key
    when:
      event:
        - push
        - pull_request

  build_and_push_image:
    image: docker:27-cli
    pull: true
    environment:
      REGISTRY_URL:
        from_secret: registry_url
      REGISTRY_USERNAME:
        from_secret: registry_username
      REGISTRY_PASSWORD:
        from_secret: registry_password
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - name: ci-secrets
        path: /secrets
    commands:
      - echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY_URL}" -u "${REGISTRY_USERNAME}" --password-stdin
      - export IMAGE_TAG="${CI_COMMIT_SHA:-latest}"
      - docker build -t "${REGISTRY_URL}/myapp:${IMAGE_TAG}" .
      - docker push "${REGISTRY_URL}/myapp:${IMAGE_TAG}"
    depends_on:
      - lint_and_test
      - fetch_secrets_from_vault

  terraform_plan:
    image: hashicorp/terraform:1.9
    pull: true
    environment:
      AWS_ACCESS_KEY_ID:
        from_secret: aws_access_key_id
      AWS_SECRET_ACCESS_KEY:
        from_secret: aws_secret_access_key
    commands:
      - cd infra/terraform
      - terraform init -input=false
      - terraform plan -input=false -out=tfplan
      # For safety, you might only upload the plan artifact or require manual apply
    when:
      event:
        - push

  terraform_apply:
    image: hashicorp/terraform:1.9
    pull: true
    environment:
      AWS_ACCESS_KEY_ID:
        from_secret: aws_access_key_id
      AWS_SECRET_ACCESS_KEY:
        from_secret: aws_secret_access_key
    commands:
      - cd infra/terraform
      - terraform init -input=false
      - terraform apply -input=false -auto-approve
    when:
      event:
        - tag # or custom deploy events / manual triggers via Woodpecker
    depends_on:
      - terraform_plan

  helm_deploy:
    image: alpine/helm:3.15.3
    pull: true
    environment:
      KUBECONFIG:
        from_secret: kubeconfig
    commands:
      - cd infra/helm
      - export IMAGE_TAG="${CI_COMMIT_SHA:-latest}"
      - helm upgrade --install myapp ./chart \
          --set image.repository="${REGISTRY_URL}/myapp" \
          --set image.tag="${IMAGE_TAG}"
    depends_on:
      - build_and_push_image
    when:
      event:
        - tag

volumes:

- name: ci-secrets
    temp: {}

Notes for your use case:
 • CI_COMMIT_SHA and friends are built-in env vars provided by Woodpecker for the current commit, branch, tag, etc.  ￼
 • The Vault step is just one style: you can also skip this and store AWS creds directly as Woodpecker secrets, or build a little “secrets init” script that writes env files the later steps source.  ￼
 • The volume ci-secrets is a temporary shared workspace between steps (Woodpecker supports named volumes to move files between steps).  ￼

⸻

If you want, next step I can:
 • Trim this into a “Dirama standard template” repo layout (folders: app/, infra/terraform/, infra/helm/, .woodpecker.yml),
 • Or add per-branch deploy patterns (e.g. tag → prod, branch name → dev namespace in K8s, etc.).
