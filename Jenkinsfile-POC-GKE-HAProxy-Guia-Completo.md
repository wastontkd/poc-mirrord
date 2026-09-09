# Jenkinsfile da POC GKE + HAProxy — Guia Completo

## 1. Objetivo

Este documento explica, em detalhes, o `Jenkinsfile` utilizado na POC com:

- Jenkins;
- Google Kubernetes Engine (GKE);
- Portal web;
- Aplicações WEB1 e WEB2;
- HAProxy;
- Namespaces separados;
- Services internos;
- Service externo do tipo `LoadBalancer`;
- NetworkPolicy opcional;
- teste automático de roteamento.

A ideia principal é:

```text
GitHub
   |
   v
Jenkins
   |
   v
kubectl
   |
   v
GKE
   |
   +--> gateway
   +--> portal
   +--> web1
   +--> web2
```

O Jenkins não mantém Pods funcionando. Ele apenas entrega os manifests ao Kubernetes. Depois disso, o próprio Kubernetes passa a manter o estado desejado.

---

# 2. Estrutura geral do Jenkinsfile

A pipeline usa o modelo Declarative Pipeline:

```groovy
pipeline {

    agent any

    options {
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(
            name: 'APPLY_NETWORK_POLICY',
            defaultValue: false,
            description: 'Aplicar NetworkPolicies após validar a POC'
        )
    }

    stages {
        ...
    }

    post {
        ...
    }
}
```

A estrutura conceitual é:

```text
pipeline
 |
 +-- agent
 |
 +-- options
 |
 +-- parameters
 |
 +-- stages
 |    |
 |    +-- Validar acesso ao GKE
 |    +-- Validar manifests
 |    +-- Criar Namespaces
 |    +-- Deploy Portal
 |    +-- Deploy WEB1
 |    +-- Deploy WEB2
 |    +-- Deploy HAProxy
 |    +-- NetworkPolicy
 |    +-- Teste de roteamento
 |    +-- Status
 |
 +-- post
```

---

# 3. `agent any`

```groovy
agent any
```

Significa que a pipeline pode executar em qualquer agente Jenkins disponível.

No ambiente desta POC, a execução ocorre no próprio servidor Jenkins, por exemplo:

```text
/var/lib/jenkins/workspace/gke-poc-mirrord
```

Esse host precisa ter:

- Git;
- kubectl;
- kubeconfig válido;
- acesso à API do GKE;
- permissões no cluster.

---

# 4. Checkout automático do SCM

Como o Jenkinsfile é carregado do Git, o Jenkins cria automaticamente um stage semelhante a:

```text
Declarative: Checkout SCM
```

Fluxo:

```text
GitHub
   |
   v
Checkout
   |
   v
Workspace Jenkins
```

Exemplo:

```text
Obtained Jenkinsfile from git
https://github.com/wastontkd/poc-mirrord.git
```

Depois:

```text
Fetching changes from the remote Git repository
```

e:

```text
Checking out Revision ...
```

Após isso, o repositório deve estar disponível dentro do workspace:

```text
workspace/
├── Jenkinsfile
└── k8s/
    ├── base/
    ├── portal/
    ├── web1/
    ├── web2/
    ├── gateway/
    └── network-policies/
```

Por isso:

```bash
kubectl apply -f k8s/base/namespaces.yaml
```

procura o arquivo relativo ao workspace atual.

---

# 5. `disableConcurrentBuilds()`

```groovy
options {
    disableConcurrentBuilds()
}
```

Impede duas execuções simultâneas da mesma pipeline.

Sem essa opção:

```text
Build 10 ----> kubectl apply
                  |
                  v
                 GKE
                  ^
                  |
Build 11 ----> kubectl apply
```

Isso poderia provocar alterações concorrentes nos mesmos recursos.

Com `disableConcurrentBuilds()`:

```text
Build 10
   |
   v
termina

Build 11
   |
   v
começa
```

---

# 6. Parâmetro `APPLY_NETWORK_POLICY`

```groovy
parameters {
    booleanParam(
        name: 'APPLY_NETWORK_POLICY',
        defaultValue: false,
        description: 'Aplicar NetworkPolicies após validar a POC'
    )
}
```

Cria um parâmetro booleano na interface do Jenkins.

Por padrão:

```text
APPLY_NETWORK_POLICY = false
```

A estratégia é:

```text
Primeiro:
validar comunicação

Depois:
ativar isolamento de rede
```

---

# 7. Ordem dos stages

A pipeline segue esta sequência:

```text
Validar acesso ao GKE
        |
        v
Validar manifests
        |
        v
Criar Namespaces
        |
        v
Deploy Portal
        |
        v
Deploy WEB1
        |
        v
Deploy WEB2
        |
        v
Deploy HAProxy
        |
        v
NetworkPolicy
        |
        v
Teste de roteamento
        |
        v
Status
```

Se um stage falha, normalmente os stages seguintes são pulados.

---

# 8. Stage `Validar acesso ao GKE`

```groovy
stage('Validar acesso ao GKE') {
    steps {
        sh '''
            set -e

            kubectl config current-context
            kubectl cluster-info
            kubectl get nodes -o wide
        '''
    }
}
```

Esse stage valida:

1. qual cluster está configurado;
2. se o Jenkins consegue falar com a API Kubernetes;
3. se os Nodes estão disponíveis.

---

## 8.1 `set -e`

```bash
set -e
```

Significa:

> Se qualquer comando retornar erro, encerre o script.

Isso evita que a pipeline continue após uma falha importante.

---

## 8.2 `kubectl config current-context`

```bash
kubectl config current-context
```

Mostra o contexto Kubernetes atual.

Exemplo:

```text
gke_project_us-central1-a_jenkins-teste
```

Ajuda a confirmar que a implantação ocorrerá no cluster correto.

---

## 8.3 `kubectl cluster-info`

```bash
kubectl cluster-info
```

Valida comunicação com a API Kubernetes.

Fluxo:

```text
Jenkins
   |
   | kubectl
   v
Kubernetes API Server
```

---

## 8.4 `kubectl get nodes -o wide`

```bash
kubectl get nodes -o wide
```

Exibe:

- status;
- versão;
- IP interno;
- IP externo;
- sistema operacional;
- runtime.

Se o Node estiver:

```text
Ready
```

o cluster está apto a receber workloads.

---

# 9. Stage `Validar manifests`

```groovy
stage('Validar manifests') {
    steps {
        sh '''
            set -e

            kubectl apply --dry-run=client -f ...
        '''
    }
}
```

Esse stage valida os YAMLs antes da implantação real.

Exemplo:

```bash
kubectl apply --dry-run=client -f k8s/web1/deployment.yaml
```

Ele verifica:

- sintaxe YAML;
- estrutura básica;
- campos reconhecidos;
- formato do objeto.

Não altera o cluster.

---

# 10. `--dry-run=client`

```bash
--dry-run=client
```

Significa:

> Faça a validação localmente no cliente kubectl, sem aplicar a mudança no cluster.

Fluxo:

```text
Manifest
   |
   v
kubectl valida
   |
   +--> erro -> pipeline para
   |
   v
manifest válido
```

---

# 11. Stage `Criar Namespaces`

```groovy
stage('Criar Namespaces') {
    steps {
        sh '''
            set -e
            kubectl apply -f k8s/base/namespaces.yaml
        '''
    }
}
```

Cria:

```text
gateway
portal
web1
web2
```

O uso de:

```bash
kubectl apply
```

é importante porque é idempotente.

Primeira execução:

```text
namespace/web1 created
```

Execução seguinte:

```text
namespace/web1 unchanged
```

---

# 12. Idempotência

Idempotência significa:

> Executar várias vezes deve produzir o mesmo estado final desejado.

`kubectl apply` não é simplesmente um comando de criação.

Ele significa conceitualmente:

```text
"garanta que o recurso esteja nesse estado"
```

---

# 13. Stage `Deploy Portal`

```groovy
stage('Deploy Portal') {
    steps {
        sh '''
            set -e

            kubectl apply -f k8s/portal/configmap.yaml
            kubectl apply -f k8s/portal/deployment.yaml
            kubectl apply -f k8s/portal/service.yaml

            kubectl rollout status                 deployment/portal                 -n portal                 --timeout=120s
        '''
    }
}
```

Esse stage aplica três objetos:

```text
ConfigMap
Deployment
Service
```

---

# 14. ConfigMap do Portal

```bash
kubectl apply -f k8s/portal/configmap.yaml
```

Na POC, o ConfigMap armazena o HTML.

Fluxo:

```text
ConfigMap
   |
   v
Volume
   |
   v
nginx
```

---

# 15. Deployment do Portal

```bash
kubectl apply -f k8s/portal/deployment.yaml
```

O Deployment cria e mantém o Pod.

Fluxo:

```text
Deployment
    |
    v
ReplicaSet
    |
    v
Pod
```

---

# 16. Service do Portal

```bash
kubectl apply -f k8s/portal/service.yaml
```

Cria um endereço estável:

```text
portal-service.portal.svc.cluster.local
```

O HAProxy usa esse endereço.

---

# 17. `kubectl rollout status`

```bash
kubectl rollout status     deployment/portal     -n portal     --timeout=120s
```

Esse comando aguarda o Deployment ficar pronto.

Sem isso:

```text
kubectl apply
   |
   v
pipeline continua imediatamente
```

Com `rollout status`:

```text
Deployment aplicado
   |
   v
Pod Ready?
  /   \
não   sim
 |      |
aguarda continua
```

---

# 18. `--timeout=120s`

```bash
--timeout=120s
```

Define o limite de espera.

Se o Pod não ficar disponível dentro de 120 segundos, o stage falha.

---

# 19. Stage `Deploy WEB1`

Repete a mesma lógica do Portal:

```text
ConfigMap
   |
Deployment
   |
Service
   |
rollout status
```

O endereço interno é:

```text
web1-service.web1.svc.cluster.local
```

---

# 20. Stage `Deploy WEB2`

WEB2 segue a mesma estrutura:

```text
ConfigMap
Deployment
Service
rollout
```

Isso mostra um padrão replicável para novas aplicações.

---

# 21. Stage `Deploy HAProxy`

```groovy
stage('Deploy HAProxy') {
    steps {
        sh '''
            set -e

            kubectl apply -f k8s/gateway/configmap.yaml
            kubectl apply -f k8s/gateway/deployment.yaml
            kubectl apply -f k8s/gateway/service.yaml

            kubectl rollout status                 deployment/haproxy                 -n gateway                 --timeout=120s
        '''
    }
}
```

O HAProxy também possui:

```text
ConfigMap
Deployment
Service
```

---

# 22. ConfigMap do HAProxy

O ConfigMap contém o:

```text
haproxy.cfg
```

Fluxo:

```text
ConfigMap
   |
   v
Volume
   |
   v
/usr/local/etc/haproxy/haproxy.cfg
   |
   v
HAProxy
```

---

# 23. Deployment do HAProxy

Cria o Pod no namespace:

```text
gateway
```

Fluxo:

```text
Deployment/haproxy
       |
       v
Pod/haproxy-xxxxx
```

---

# 24. Service do HAProxy

O HAProxy usa:

```yaml
type: LoadBalancer
```

No GKE:

```text
Internet
   |
   v
Google Cloud Load Balancer
   |
   v
Service haproxy-service
   |
   v
HAProxy Pod
```

---

# 25. Comunicação entre namespaces

O HAProxy está em:

```text
gateway
```

mas acessa:

```text
portal-service.portal.svc.cluster.local
web1-service.web1.svc.cluster.local
web2-service.web2.svc.cluster.local
```

Formato:

```text
<service>.<namespace>.svc.cluster.local
```

Esse é o conceito principal da POC.

---

# 26. Stage `NetworkPolicy`

```groovy
stage('NetworkPolicy') {
    when {
        expression {
            return params.APPLY_NETWORK_POLICY
        }
    }
```

O bloco `when` decide se o stage será executado.

Se:

```text
APPLY_NETWORK_POLICY=false
```

o stage é ignorado.

Se:

```text
APPLY_NETWORK_POLICY=true
```

executa:

```bash
kubectl apply -f k8s/network-policies/
```

---

# 27. Aplicando um diretório

```bash
kubectl apply -f k8s/network-policies/
```

Aplica todos os manifests válidos do diretório.

Exemplo:

```text
network-policies/
├── portal.yaml
├── web1.yaml
└── web2.yaml
```

---

# 28. Stage `Teste de roteamento`

Esse stage é especialmente importante.

Ele não verifica apenas:

```text
Pod = Running
```

Ele testa uma requisição HTTP passando pelo HAProxy.

---

# 29. Pod temporário de teste

```bash
TEST_POD="poc-routing-test"
```

Depois:

```bash
kubectl run "$TEST_POD"     -n gateway     --image=busybox:1.36     --restart=Never     --command -- sleep 300
```

Cria:

```text
gateway
   |
   v
Pod poc-routing-test
```

---

# 30. Por que testar de dentro do cluster

Isso valida:

```text
Pod teste
   |
   v
DNS Kubernetes
   |
   v
Service HAProxy
   |
   v
HAProxy
   |
   v
Service aplicação
   |
   v
Pod aplicação
```

É um teste de integração muito melhor do que apenas verificar se os Pods estão `Running`.

---

# 31. `kubectl wait`

```bash
kubectl wait     --for=condition=Ready     pod/"$TEST_POD"     -n gateway     --timeout=60s
```

A pipeline só continua quando o Pod temporário estiver `Ready`.

---

# 32. Teste do Portal

```bash
kubectl exec -n gateway "$TEST_POD" --     wget -qO- http://haproxy-service.gateway.svc.cluster.local/     | grep "Portal de Aplicações"
```

Fluxo:

```text
Pod teste
   |
   v
haproxy-service
   |
   v
HAProxy
   |
   v
portal-service
   |
   v
Portal Pod
```

O `grep` valida o conteúdo da resposta.

---

# 33. Teste WEB1

```text
http://haproxy-service.gateway.svc.cluster.local/web1/
```

Fluxo:

```text
Pod teste
   |
   v
HAProxy
   |
   | /web1/
   v
backend_web1
   |
   v
web1-service.web1.svc.cluster.local
   |
   v
WEB1 Pod
```

---

# 34. Teste WEB2

Mesma lógica:

```text
/web2/
```

deve retornar conteúdo contendo:

```text
Aplicação WEB 2
```

---

# 35. Função `cleanup`

```bash
cleanup() {
    kubectl delete pod "$TEST_POD"         -n gateway         --ignore-not-found         --wait=false         >/dev/null 2>&1 || true
}
```

Remove o Pod temporário ao final.

---

# 36. `trap cleanup EXIT`

```bash
trap cleanup EXIT
```

Instrui o shell:

> Sempre execute `cleanup` quando este script terminar.

Funciona tanto em sucesso quanto em falha.

```text
Teste OK
   |
   v
cleanup

Teste FAIL
   |
   v
cleanup
```

---

# 37. `--ignore-not-found`

```bash
--ignore-not-found
```

Evita erro se o Pod já não existir.

---

# 38. `--wait=false`

```bash
--wait=false
```

Solicita a exclusão sem esperar o recurso desaparecer completamente.

---

# 39. `>/dev/null 2>&1`

Descarta stdout e stderr:

```bash
>/dev/null 2>&1
```

É usado para manter o log mais limpo.

---

# 40. `|| true`

```bash
|| true
```

Significa:

> Mesmo se o comando anterior falhar, considere esta linha bem-sucedida.

Muito útil em comandos de limpeza e troubleshooting.

---

# 41. Stage `Status`

```groovy
stage('Status') {
```

Exibe uma visão geral dos recursos.

Exemplos:

```bash
kubectl get all -n gateway -o wide
kubectl get all -n portal -o wide
kubectl get all -n web1 -o wide
kubectl get all -n web2 -o wide
```

---

# 42. Verificando o LoadBalancer

```bash
kubectl get svc haproxy-service -n gateway
```

Quando o GKE provisiona o Load Balancer:

```text
EXTERNAL-IP
34.x.x.x
```

O acesso poderá ser feito em:

```text
http://34.x.x.x/
http://34.x.x.x/web1/
http://34.x.x.x/web2/
```

---

# 43. Bloco `post`

```groovy
post {
    failure {
        ...
    }
}
```

O bloco `post` executa ações após os stages.

Neste Jenkinsfile, os comandos executam somente em caso de falha.

---

# 44. Diagnóstico automático

```bash
kubectl get pods -A -o wide || true
```

Ajuda a identificar estados como:

```text
Pending
CrashLoopBackOff
ImagePullBackOff
Error
```

---

# 45. Eventos Kubernetes

```bash
kubectl get events -A     --sort-by='.lastTimestamp'     | tail -50 || true
```

Ajuda a encontrar problemas de:

- scheduler;
- image pull;
- CPU;
- memória;
- probes;
- volumes;
- LoadBalancer;
- rede.

---

# 46. Erro `exit code 126` encontrado durante a POC

Foi encontrado:

```text
/bin: Permission denied
```

e:

```text
script returned exit code 126
```

O problema era um comentário Groovy dentro de um bloco shell:

```groovy
sh '''
    /* groovylint-disable-next-line LineLength */
'''
```

Dentro de `sh`, essa sintaxe não é comentário.

O shell interpreta:

```text
/*
```

como wildcard e expande para:

```text
/bin
/boot
/dev
/etc
/home
...
```

Depois tenta executar `/bin`.

Resultado:

```text
/bin: Permission denied
```

---

# 47. Comentário correto dentro de `sh`

Dentro de:

```groovy
sh '''
...
'''
```

use:

```bash
# comentário
```

Exemplo:

```groovy
sh '''
    # Aguarda o deployment
    kubectl rollout status deployment/portal -n portal
'''
```

---

# 48. Comentários Groovy

Fora do bloco shell, podem ser utilizados:

```groovy
// comentário
```

ou:

```groovy
/*
 comentário
*/
```

Mas dentro do `sh`, use sintaxe do shell.

---

# 49. Fluxo completo da pipeline

```text
GitHub
   |
   v
Checkout SCM
   |
   v
Validar acesso ao GKE
   |
   v
Validar manifests
   |
   v
Criar Namespaces
   |
   v
Deploy Portal
   |
   v
Deploy WEB1
   |
   v
Deploy WEB2
   |
   v
Deploy HAProxy
   |
   v
NetworkPolicy opcional
   |
   v
Teste de roteamento
   |
   v
Status final
```

---

# 50. Fluxo da aplicação após o deploy

```text
Usuário
   |
   v
GKE Load Balancer
   |
   v
haproxy-service
   |
   v
HAProxy
   |
   +------------------+
   |        |         |
   v        v         v
Portal     WEB1      WEB2
Service    Service   Service
   |        |         |
   v        v         v
Pod        Pod       Pod
```

---

# 51. Responsabilidade do Jenkins

O Jenkins:

```text
- lê o Git
- executa kubectl
- valida manifests
- aplica manifests
- aguarda rollouts
- executa testes
- coleta diagnóstico
```

O Jenkins não é responsável por manter os Pods vivos.

---

# 52. Responsabilidade do Kubernetes

O Kubernetes passa a gerenciar:

```text
Deployment
ReplicaSet
Pods
Services
ConfigMaps
NetworkPolicies
LoadBalancer
```

Se um Pod morrer:

```text
Pod morre
   |
   v
Deployment Controller
   |
   v
novo Pod
```

O Jenkins não precisa intervir.

---

# 53. Git como fonte da configuração

A estrutura versionada é:

```text
Git
 |
 +-- Jenkinsfile
 |
 +-- k8s/
     |
     +-- deployments
     +-- services
     +-- configmaps
     +-- networkpolicies
```

Isso facilita:

- auditoria;
- revisão;
- rollback;
- histórico;
- colaboração.

---

# 54. Exemplo de mudança futura

Alterar:

```yaml
replicas: 1
```

para:

```yaml
replicas: 3
```

Depois:

```text
git commit
git push
Jenkins
kubectl apply
```

O Kubernetes escala:

```text
WEB1
 |
 +--> Pod 1
 +--> Pod 2
 +--> Pod 3
```

O HAProxy continua apontando para:

```text
web1-service.web1.svc.cluster.local
```

---

# 55. Benefícios da pipeline atual

Principais pontos positivos:

- manifests separados do Jenkinsfile;
- implantação declarativa;
- `kubectl apply`;
- validação com `dry-run`;
- `rollout status`;
- teste funcional;
- diagnóstico automático;
- separação por namespace;
- integração com GKE.

---

# 56. Melhorias futuras

Algumas evoluções possíveis:

## Validação server-side

```bash
kubectl apply     --dry-run=server     -f arquivo.yaml
```

## `kubectl diff`

```bash
kubectl diff -f arquivo.yaml || true
```

## Versões fixas de imagens

Evitar:

```text
nginx:alpine
```

Preferir uma versão explícita.

## Helm

Reduzir repetição de manifests.

## Argo CD ou Flux

Separar:

```text
Jenkins = CI
Argo CD = CD
```

---

# 57. Resumo dos comandos mais importantes

| Comando | Função |
|---|---|
| `kubectl config current-context` | Mostra o cluster atual |
| `kubectl cluster-info` | Testa acesso ao cluster |
| `kubectl get nodes` | Verifica Nodes |
| `kubectl apply --dry-run=client` | Valida manifest localmente |
| `kubectl apply -f` | Aplica manifesto |
| `kubectl rollout status` | Aguarda Deployment |
| `kubectl run` | Cria Pod temporário |
| `kubectl wait` | Aguarda condição |
| `kubectl exec` | Executa comando dentro do Pod |
| `kubectl get all` | Lista recursos principais |
| `kubectl get events` | Consulta eventos |
| `kubectl delete pod` | Remove Pod |
| `kubectl get svc` | Consulta Service |

---

# 58. Resumo conceitual do Jenkinsfile

O Jenkinsfile pode ser entendido como:

```text
1. Verifique o cluster.

2. Valide os manifests.

3. Crie os namespaces.

4. Implante o Portal.

5. Implante WEB1.

6. Implante WEB2.

7. Implante o HAProxy.

8. Aplique segurança de rede se solicitado.

9. Faça requisições reais através do HAProxy.

10. Mostre o estado final.

11. Se falhar, colete Pods e eventos.
```

---

# 59. Conceito principal da POC

O HAProxy não aponta para Pods.

Ele aponta para Services:

```text
HAProxy
namespace gateway
      |
      +--> portal-service.portal.svc.cluster.local
      |
      +--> web1-service.web1.svc.cluster.local
      |
      +--> web2-service.web2.svc.cluster.local
```

Isso permite que o Kubernetes:

- recrie Pods;
- altere IPs;
- escale réplicas;
- mova Pods entre Nodes;

sem exigir alteração no HAProxy.

---

# 60. Conclusão

O Jenkinsfile demonstra vários conceitos importantes de CI/CD e Kubernetes:

- Git;
- Jenkins;
- GKE;
- manifests declarativos;
- namespaces;
- Deployments;
- Services;
- ConfigMaps;
- HAProxy;
- DNS interno;
- comunicação entre namespaces;
- LoadBalancer;
- NetworkPolicy;
- rollout;
- teste automatizado;
- troubleshooting.

Ele serve como uma boa base para evoluir depois para:

```text
Build da imagem
   |
   v
Artifact Registry
   |
   v
Jenkins
   |
   v
GKE
   |
   v
HAProxy / Gateway
   |
   v
Aplicações
```

e posteriormente para uma arquitetura GitOps com Jenkins + Argo CD ou Flux.
