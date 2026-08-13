#!/usr/bin/env bash
# Local RecipeAI Argo pipeline on kind + podman.
#
# Usage:
#   export OPENAI_API_KEY=sk-...
#   ./hack/run-workflow.sh setup            # install tools, kind cluster, Argo, MinIO
#   ./hack/run-workflow.sh build            # build + load images with podman
#   ./hack/run-workflow.sh deploy           # MCP server + secrets
#   ./hack/run-workflow.sh submit           # submit workflow
#   ./hack/run-workflow.sh all              # setup → build → deploy → submit
#   ./hack/run-workflow.sh all --mode ingredient --request "chicken, rice"
#
# Env:
#   CLUSTER_NAME   kind cluster name (default: recipeai)
#   NAMESPACE      workflow namespace (default: recipeai)
#   ARGO_VERSION   Argo Workflows release tag (default: v4.1.0)
#   SKIP_BREW=1    do not brew install missing tools

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NAMESPACE="${NAMESPACE:-recipeai}"
CLUSTER_NAME="${CLUSTER_NAME:-recipeai}"
ARGO_VERSION="${ARGO_VERSION:-v4.1.0}"
ARTIFACT_CM="k8s/argo/artifact-repo-configmap.yaml"
WORKFLOW="k8s/argo/workflow.yaml"
MINIO_MANIFEST="hack/manifests/minio.yaml"
RUNTIME=podman
export KIND_EXPERIMENTAL_PROVIDER=podman

IMAGES=(
  "recipeai-planner:latest:images/Containerfile.planner"
  "recipeai-chef:latest:images/Containerfile.chef"
  "recipeai-nutrition:latest:images/Containerfile.nutrition"
  "recipeai-mcp-server:latest:images/Containerfile.mcp-server"
)

die() { echo "error: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "$1 not found (run: ./hack/run-workflow.sh setup)"; }

ensure_brew_pkg() {
  local pkg="$1"
  local bin="${2:-$1}"
  if command -v "$bin" >/dev/null; then
    return
  fi
  [[ "${SKIP_BREW:-0}" == "1" ]] && die "$bin missing and SKIP_BREW=1"
  command -v brew >/dev/null || die "homebrew required to install $pkg"
  echo "==> brew install $pkg"
  brew install "$pkg"
}

ensure_tools() {
  echo "==> Ensuring CLI tools (podman, kind, kubectl, argo)"
  ensure_brew_pkg podman
  ensure_brew_pkg kind
  ensure_brew_pkg kubectl
  ensure_brew_pkg argo
}

ensure_podman_machine() {
  need podman
  echo "==> Ensuring podman machine (rootful, for kind)"
  if ! podman machine list --format '{{.Name}}' 2>/dev/null | grep -q .; then
    podman machine init --rootful --cpus 4 --memory 8192 --disk-size 60
  fi
  # Prefer rootful for kind reliability on macOS
  local rootful
  rootful="$(podman machine inspect --format '{{.Rootful}}' 2>/dev/null | head -1 || true)"
  if [[ "$rootful" != "true" ]]; then
    echo "==> Recreating podman machine as rootful (kind needs this on macOS)"
    podman machine stop 2>/dev/null || true
    podman machine rm -f 2>/dev/null || true
    podman machine init --rootful --cpus 4 --memory 8192 --disk-size 60
  fi
  if ! podman machine inspect --format '{{.State}}' 2>/dev/null | grep -qi running; then
    podman machine start
  fi
  podman info >/dev/null
}

ensure_kind_cluster() {
  need kind
  need kubectl
  export KIND_EXPERIMENTAL_PROVIDER=podman

  local exists=0
  if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
    exists=1
  fi

  if [[ "$exists" -eq 1 ]]; then
    echo "==> kind cluster '$CLUSTER_NAME' already exists"
    kind export kubeconfig --name "$CLUSTER_NAME"
    if ! kubectl --context "kind-${CLUSTER_NAME}" cluster-info >/dev/null 2>&1; then
      echo "==> Cluster API not reachable; recreating kind cluster"
      kind delete cluster --name "$CLUSTER_NAME"
      exists=0
    fi
  fi

  if [[ "$exists" -eq 0 ]]; then
    echo "==> Creating kind cluster '$CLUSTER_NAME' (provider=podman)"
    # Clean up orphaned nodes if a previous create partially failed
    if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME" \
      || podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q "${CLUSTER_NAME}-"; then
      kind delete cluster --name "$CLUSTER_NAME" 2>/dev/null || true
    fi
    kind create cluster --name "$CLUSTER_NAME"
  fi

  kind export kubeconfig --name "$CLUSTER_NAME"
  kubectl config use-context "kind-${CLUSTER_NAME}" >/dev/null
  # Wait for API after podman restarts
  local i
  for i in $(seq 1 30); do
    if kubectl cluster-info >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  kubectl cluster-info >/dev/null || die "kind cluster API not reachable"
  echo "==> kubectl context: $(kubectl config current-context)"
}

install_argo() {
  need kubectl
  echo "==> Installing Argo Workflows $ARGO_VERSION"
  kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
  # Server-side apply avoids CRD annotation size limits on large Argo manifests.
  kubectl apply --server-side --force-conflicts -n argo \
    -f "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_VERSION}/install.yaml"
  echo "==> Waiting for Argo workflow-controller"
  kubectl -n argo rollout status deploy/workflow-controller --timeout=180s
  kubectl -n argo rollout status deploy/argo-server --timeout=180s || true
}

install_minio() {
  need kubectl
  kubectl apply -f k8s/namespace.yaml
  echo "==> Installing MinIO artifact store"
  kubectl apply -f "$MINIO_MANIFEST"
  kubectl -n "$NAMESPACE" rollout status deploy/minio --timeout=180s
  # Recreate bucket job if a previous run finished
  kubectl -n "$NAMESPACE" delete job minio-create-bucket --ignore-not-found
  kubectl apply -f "$MINIO_MANIFEST"
  kubectl -n "$NAMESPACE" wait --for=condition=complete job/minio-create-bucket --timeout=120s
  kubectl apply -f "$ARTIFACT_CM"
}

configure_workflow_rbac() {
  echo "==> Granting workflow SA permissions in $NAMESPACE"
  kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$NAMESPACE" create serviceaccount argo-workflow --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$NAMESPACE" create rolebinding argo-workflow-admin \
    --clusterrole=admin \
    --serviceaccount="${NAMESPACE}:argo-workflow" \
    --dry-run=client -o yaml | kubectl apply -f -
  # Also allow default SA (workflow.yaml does not set serviceAccountName)
  kubectl -n "$NAMESPACE" create rolebinding default-admin \
    --clusterrole=admin \
    --serviceaccount="${NAMESPACE}:default" \
    --dry-run=client -o yaml | kubectl apply -f -
}

setup() {
  ensure_tools
  ensure_podman_machine
  ensure_kind_cluster
  install_argo
  configure_workflow_rbac
  install_minio
  echo "==> Setup complete"
  echo "    Cluster: kind-$CLUSTER_NAME"
  echo "    Next: export OPENAI_API_KEY=... && ./hack/run-workflow.sh all"
}

build_images() {
  need podman
  echo "==> Building images with podman"
  local entry name tag file
  for entry in "${IMAGES[@]}"; do
    IFS=: read -r name tag file <<<"$entry"
    echo "--- $name:$tag ($file)"
    podman build -f "$file" -t "$name:$tag" .
  done
}

load_images() {
  need kind
  need podman
  export KIND_EXPERIMENTAL_PROVIDER=podman
  kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME" \
    || die "kind cluster '$CLUSTER_NAME' not found (run: ./hack/run-workflow.sh setup)"
  echo "==> Loading images into kind/$CLUSTER_NAME"
  local entry name tag
  for entry in "${IMAGES[@]}"; do
    IFS=: read -r name tag _ <<<"$entry"
    echo "--- load $name:$tag"
    podman save "$name:$tag" | kind load image-archive - --name "$CLUSTER_NAME"
  done
}

apply_secret() {
  [[ -n "${OPENAI_API_KEY:-}" ]] || die "OPENAI_API_KEY is required"
  echo "==> Applying secret from OPENAI_API_KEY"
  kubectl apply -f k8s/namespace.yaml
  kubectl -n "$NAMESPACE" create secret generic recipeai-secrets \
    --from-literal=openai-api-key="$OPENAI_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -
}

deploy() {
  need kubectl
  echo "==> Applying MCP server + service"
  kubectl apply -k k8s/
  apply_secret
  kubectl apply -f "$ARTIFACT_CM"
  echo "==> Waiting for MCP server"
  kubectl -n "$NAMESPACE" rollout status deploy/recipeai-mcp-server --timeout=180s
}

submit() {
  need argo
  need kubectl
  local -a extra=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)              extra+=(-p "mode=$2"); shift 2 ;;
      --cuisine)           extra+=(-p "cuisine=$2"); shift 2 ;;
      --max-prep-time)     extra+=(-p "max-prep-time=$2"); shift 2 ;;
      --dietary-needs)     extra+=(-p "dietary-needs=$2"); shift 2 ;;
      --request)           extra+=(-p "request=$2"); shift 2 ;;
      --nutrition-goals)   extra+=(-p "nutrition-goals=$2"); shift 2 ;;
      -p|--parameter)      extra+=(-p "$2"); shift 2 ;;
      *) die "unknown submit arg: $1" ;;
    esac
  done
  echo "==> Submitting workflow"
  argo submit -n "$NAMESPACE" "$WORKFLOW" --watch "${extra[@]}"
}

usage() {
  sed -n '2,18p' "$0" | sed -E 's/^# ?//'
}

cmd="${1:-all}"
shift || true

case "$cmd" in
  -h|--help|help) usage ;;
  setup) setup ;;
  build)
    build_images
    load_images
    ;;
  deploy) deploy ;;
  submit) submit "$@" ;;
  all)
    setup
    build_images
    load_images
    deploy
    submit "$@"
    ;;
  *)
    die "unknown command: $cmd (setup|build|deploy|submit|all)"
    ;;
esac
