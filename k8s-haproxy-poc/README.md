# POC GKE — Portal + HAProxy + Namespaces

Esta versão da POC separa cada objeto Kubernetes em arquivos individuais para facilitar o estudo.

## Estrutura

```text
k8s-haproxy-poc/
├── Jenkinsfile
├── README.md
└── k8s/
    ├── base/
    │   └── namespaces.yaml
    │
    ├── portal/
    │   ├── configmap.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── index.html
    │
    ├── web1/
    │   ├── configmap.yaml
    │   ├── deployment.yaml
    │   └── service.yaml
    │
    ├── web2/
    │   ├── configmap.yaml
    │   ├── deployment.yaml
    │   └── service.yaml
    │
    ├── gateway/
    │   ├── haproxy.cfg
    │   ├── configmap.yaml
    │   ├── deployment.yaml
    │   └── service.yaml
    │
    └── network-policies/
        ├── portal.yaml
        ├── web1.yaml
        └── web2.yaml
```

## Como ler esta POC

A melhor ordem para entender o fluxo é:

1. `k8s/base/namespaces.yaml`
2. `k8s/web1/deployment.yaml`
3. `k8s/web1/service.yaml`
4. `k8s/gateway/haproxy.cfg`
5. `k8s/gateway/configmap.yaml`
6. `k8s/gateway/deployment.yaml`
7. `k8s/gateway/service.yaml`
8. `Jenkinsfile`

Depois compare WEB1 com WEB2 e Portal.

---

# Deployment

O Deployment define **como os Pods devem existir**.

Exemplo:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web1
  namespace: web1
spec:
  replicas: 1
```

O Kubernetes garante que exista a quantidade desejada de Pods.

A associação Deployment → Pod usa labels:

```yaml
selector:
  matchLabels:
    app: web1
```

e:

```yaml
template:
  metadata:
    labels:
      app: web1
```

---

# Service

O Service fornece um endereço estável para os Pods.

```yaml
selector:
  app: web1
```

Ele encontra todos os Pods que tenham:

```yaml
labels:
  app: web1
```

O HAProxy não conhece o IP do Pod.

Ele conhece:

```text
web1-service.web1.svc.cluster.local
```

Fluxo:

```text
HAProxy
   |
   v
Service
   |
   v
Pod
```

---

# ConfigMap

O ConfigMap armazena configuração que não é segredo.

Na POC ele é usado para:

- armazenar o HTML das aplicações;
- armazenar a configuração do HAProxy.

No HAProxy:

```yaml
volumes:
  - name: haproxy-config
    configMap:
      name: haproxy-config
```

e:

```yaml
volumeMounts:
  - name: haproxy-config
    mountPath: /usr/local/etc/haproxy/haproxy.cfg
    subPath: haproxy.cfg
```

Fluxo:

```text
ConfigMap
   |
   v
Volume Kubernetes
   |
   v
/usr/local/etc/haproxy/haproxy.cfg
   |
   v
Container HAProxy
```

---

# haproxy.cfg

Este é o arquivo que contém a lógica de proxy.

```haproxy
frontend http_front
    bind *:8080
```

O HAProxy escuta na porta `8080`.

As ACLs identificam o caminho:

```haproxy
acl route_web1 path_reg ^/web1(/|$)
acl route_web2 path_reg ^/web2(/|$)
```

Depois selecionam o backend:

```haproxy
use_backend backend_web1 if route_web1
use_backend backend_web2 if route_web2
```

Todo o restante vai para:

```haproxy
default_backend backend_portal
```

WEB1:

```haproxy
server web1 web1-service.web1.svc.cluster.local:80 check
```

WEB2:

```haproxy
server web2 web2-service.web2.svc.cluster.local:80 check
```

É aqui que acontece a comunicação entre namespaces.

---

# Service do HAProxy

O arquivo:

```text
k8s/gateway/service.yaml
```

possui:

```yaml
type: LoadBalancer
```

No GKE isso expõe o HAProxy externamente.

Fluxo:

```text
Internet
    |
    v
GKE Load Balancer
    |
    v
Service haproxy-service
    |
    v
Pod HAProxy
```

---

# Arquitetura completa

```text
INTERNET
   |
   v
GKE LoadBalancer
   |
   v
haproxy-service
namespace gateway
   |
   v
HAProxy Pod
   |
   +-------------------------+
   |            |            |
   v            v            v
Portal         WEB1         WEB2
Service        Service      Service
   |            |            |
   v            v            v
Pod            Pod          Pod
portal         web1         web2
```

---

# Comunicação entre namespaces

```text
gateway
   |
   +--> portal-service.portal.svc.cluster.local
   |
   +--> web1-service.web1.svc.cluster.local
   |
   +--> web2-service.web2.svc.cluster.local
```

O formato do DNS é:

```text
<service>.<namespace>.svc.cluster.local
```

---

# Aplicação manual

Primeiro:

```bash
kubectl apply -f k8s/base/namespaces.yaml
```

Portal:

```bash
kubectl apply -f k8s/portal/configmap.yaml
kubectl apply -f k8s/portal/deployment.yaml
kubectl apply -f k8s/portal/service.yaml
```

WEB1:

```bash
kubectl apply -f k8s/web1/configmap.yaml
kubectl apply -f k8s/web1/deployment.yaml
kubectl apply -f k8s/web1/service.yaml
```

WEB2:

```bash
kubectl apply -f k8s/web2/configmap.yaml
kubectl apply -f k8s/web2/deployment.yaml
kubectl apply -f k8s/web2/service.yaml
```

HAProxy:

```bash
kubectl apply -f k8s/gateway/configmap.yaml
kubectl apply -f k8s/gateway/deployment.yaml
kubectl apply -f k8s/gateway/service.yaml
```

---

# Validação

```bash
kubectl get pods -A
```

```bash
kubectl get svc -A
```

```bash
kubectl get svc haproxy-service -n gateway
```

---

# NetworkPolicy

As políticas estão separadas porque recomendo validar primeiro a POC sem isolamento.

Depois:

```bash
kubectl apply -f k8s/network-policies/
```

A intenção é permitir:

```text
gateway ---> portal
gateway ---> web1
gateway ---> web2
```

e restringir acessos de origem não autorizada aos Pods selecionados.

---

# Jenkins

O `Jenkinsfile` não gera mais os manifests.

Ele somente:

```text
Git Repository
     |
     v
Jenkins
     |
     v
kubectl apply
     |
     v
GKE
```

Isso permite observar e versionar exatamente o que será implantado.

É uma estrutura mais adequada para aprendizado e também uma base melhor para evoluir posteriormente para GitOps.
