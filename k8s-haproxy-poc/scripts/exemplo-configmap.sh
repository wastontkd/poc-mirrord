#!/usr/bin/env bash
set -e

echo "Exemplo: gerar ConfigMap do HAProxy diretamente do haproxy.cfg:"
echo
echo "kubectl create configmap haproxy-config \"
echo "  --from-file=haproxy.cfg=k8s/gateway/haproxy.cfg \"
echo "  -n gateway \"
echo "  --dry-run=client -o yaml"
echo
echo "O arquivo k8s/gateway/configmap.yaml já contém o equivalente declarativo."
