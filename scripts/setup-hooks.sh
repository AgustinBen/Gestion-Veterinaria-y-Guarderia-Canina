#!/bin/sh
# Activa los hooks versionados del repo. Un solo comando por clon.
set -eu

raiz=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "setup-hooks: hay que ejecutarlo dentro del repositorio." >&2
  exit 1
}
cd "$raiz"

# En Windows el bit de ejecución no existe, pero en Linux/macOS sí hace falta.
chmod +x .githooks/commit-msg .githooks/pre-commit 2>/dev/null || true

git config core.hooksPath .githooks

echo "Hooks activos: core.hooksPath=$(git config --get core.hooksPath)"
echo "  commit-msg: valida Conventional Commits."
echo "  pre-commit: pytest en backend; npm test si hay cambios en frontend."
