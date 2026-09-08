pipeline {

    agent any

    options {
        disableConcurrentBuilds()
    }

    parameters {

        booleanParam(
            name: 'APPLY_NETWORK_POLICY',
            defaultValue: false,
            description: 'Aplicar NetworkPolicy restringindo o acesso às aplicações somente ao namespace gateway'
        )
    }

    environment {
        MANIFEST_DIR = 'k8s-poc'
    }

    stages {

        // ============================================================
        // VALIDAR ACESSO AO CLUSTER
        // ============================================================

        stage('Validar acesso ao GKE') {

            steps {

                sh '''
                    set -e

                    echo "============================================"
                    echo "Contexto atual do kubectl"
                    echo "============================================"

                    kubectl config current-context

                    echo
                    echo "============================================"
                    echo "Cluster"
                    echo "============================================"

                    kubectl cluster-info

                    echo
                    echo "============================================"
                    echo "Nodes"
                    echo "============================================"

                    kubectl get nodes -o wide
                '''
            }
        }


        // ============================================================
        // GERAR DIRETORIO
        // ============================================================

        stage('Preparar manifests') {

            steps {

                sh '''
                    rm -rf "$MANIFEST_DIR"
                    mkdir -p "$MANIFEST_DIR"
                '''
            }
        }


        // ============================================================
        // NAMESPACES
        // ============================================================

        stage('Gerar Namespaces') {

            steps {

                writeFile(
                    file: "${env.MANIFEST_DIR}/00-namespaces.yaml",
                    text: '''
apiVersion: v1
kind: Namespace
metadata:
  name: gateway

---
apiVersion: v1
kind: Namespace
metadata:
  name: portal

---
apiVersion: v1
kind: Namespace
metadata:
  name: web1

---
apiVersion: v1
kind: Namespace
metadata:
  name: web2
'''
                )
            }
        }


        // ============================================================
        // PORTAL
        // ============================================================

        stage('Gerar Portal') {

            steps {

                writeFile(
                    file: "${env.MANIFEST_DIR}/10-portal.yaml",
                    text: '''
apiVersion: v1
kind: ConfigMap

metadata:
  name: portal-html
  namespace: portal

data:

  index.html: |
    <!DOCTYPE html>

    <html lang="pt-BR">

    <head>

        <meta charset="UTF-8">

        <title>Portal Kubernetes</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                background: #1e293b;
                color: white;
                text-align: center;
                padding-top: 100px;
            }

            h1 {
                margin-bottom: 40px;
            }

            .apps {
                display: flex;
                justify-content: center;
                gap: 30px;
            }

            .app {
                padding: 30px 60px;
                background: #334155;
                border-radius: 10px;
                text-decoration: none;
                color: white;
                font-size: 24px;
            }

            .app:hover {
                background: #475569;
            }

        </style>

    </head>

    <body>

        <h1>Portal de Aplicações</h1>

        <div class="apps">

            <a class="app" href="/web1/">
                WEB 1
            </a>

            <a class="app" href="/web2/">
                WEB 2
            </a>

        </div>

    </body>

    </html>


---
apiVersion: apps/v1
kind: Deployment

metadata:
  name: portal
  namespace: portal

spec:

  replicas: 1

  selector:

    matchLabels:
      app: portal

  template:

    metadata:

      labels:
        app: portal

    spec:

      containers:

        - name: portal

          image: nginx:alpine

          ports:

            - name: http
              containerPort: 80

          volumeMounts:

            - name: html
              mountPath: /usr/share/nginx/html/index.html
              subPath: index.html

          readinessProbe:

            httpGet:
              path: /
              port: 80

            initialDelaySeconds: 2
            periodSeconds: 5

          livenessProbe:

            httpGet:
              path: /
              port: 80

            initialDelaySeconds: 5
            periodSeconds: 10

          resources:

            requests:
              cpu: 25m
              memory: 32Mi

            limits:
              cpu: 100m
              memory: 64Mi

      volumes:

        - name: html

          configMap:
            name: portal-html


---
apiVersion: v1
kind: Service

metadata:
  name: portal-service
  namespace: portal

spec:

  selector:
    app: portal

  ports:

    - name: http
      port: 80
      targetPort: 80

  type: ClusterIP
'''
                )
            }
        }


        // ============================================================
        // WEB1
        // ============================================================

        stage('Gerar WEB1') {

            steps {

                writeFile(
                    file: "${env.MANIFEST_DIR}/20-web1.yaml",
                    text: '''
apiVersion: v1
kind: ConfigMap

metadata:
  name: web1-html
  namespace: web1

data:

  index.html: |
    <!DOCTYPE html>

    <html lang="pt-BR">

    <head>

        <meta charset="UTF-8">

        <title>WEB 1</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                background: #0f172a;
                color: white;
                text-align: center;
                padding-top: 100px;
            }

            h1 {
                font-size: 50px;
            }

            .info {
                font-size: 20px;
                margin: 30px;
            }

            a {
                color: #38bdf8;
            }

        </style>

    </head>

    <body>

        <h1>Aplicação WEB 1</h1>

        <div class="info">
            Namespace: <strong>web1</strong>
        </div>

        <p>
            Requisição encaminhada pelo HAProxy.
        </p>

        <a href="/">
            Voltar para o Portal
        </a>

    </body>

    </html>


---
apiVersion: apps/v1
kind: Deployment

metadata:
  name: web1
  namespace: web1

spec:

  replicas: 1

  selector:

    matchLabels:
      app: web1

  template:

    metadata:

      labels:
        app: web1

    spec:

      containers:

        - name: web1

          image: nginx:alpine

          ports:

            - name: http
              containerPort: 80

          volumeMounts:

            - name: html
              mountPath: /usr/share/nginx/html/index.html
              subPath: index.html

          readinessProbe:

            httpGet:
              path: /
              port: 80

            initialDelaySeconds: 2
            periodSeconds: 5

          livenessProbe:

            httpGet:
              path: /
              port: 80

            initialDelaySeconds: 5
            periodSeconds: 10

          resources:

            requests:
              cpu: 25m
              memory: 32Mi

            limits:
              cpu: 100m
              memory: 64Mi

      volumes:

        - name: html

          configMap:
            name: web1-html


---
apiVersion: v1
kind: Service

metadata:
  name: web1-service
  namespace: web1

spec:

  selector:
    app: web1

  ports:

    - name: http
      port: 80
      targetPort: 80

  type: ClusterIP
'''
                )
            }
        }


        // ============================================================
        // WEB2
        // ============================================================

        stage('Gerar WEB2') {

            steps {

                writeFile(
                    file: "${env.MANIFEST_DIR}/30-web2.yaml",
                    text: '''
apiVersion: v1
kind: ConfigMap

metadata:
  name: web2-html
  namespace: web2

data:

  index.html: |
    <!DOCTYPE html>

    <html lang="pt-BR">

    <head>

        <meta charset="UTF-8">

        <title>WEB 2</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                background: #312e81;
                color: white;
                text-align: center;
                padding-top: 100px;
            }

            h1 {
                font-size: 50px;
            }

            .info {
                font-size: 20px;
                margin: 30px;
            }

            a {
                color: #67e8f9;
            }

        </style>

    </head>

    <body>

        <h1>Aplicação WEB 2</h1>

        <div class="info">
            Namespace: <strong>web2</strong>
        </div>

        <p>
            Requisição encaminhada pelo HAProxy.
        </p>

        <a href="/">
            Voltar para o Portal
        </a>

    </body>

    </html>


---
apiVersion: apps/v1
kind: Deployment

metadata:
  name: web2
  namespace: web2

spec:

  replicas: 1

  selector:

    matchLabels:
      app: web2

  template:

    metadata:

      labels:
        app: web2

    spec:

      containers:

        - name: web2

          image: nginx:alpine

          ports:

            - name: http
              containerPort: 80

          volumeMounts:

            - name: html
              mountPath: /usr/share/nginx/html/index.html
              subPath: index.html

          readinessProbe:

            httpGet:
              path: /
              port: 80

            initialDelaySeconds: 2
            periodSeconds: 5

          livenessProbe:

            httpGet:
              path: /
              port: 80

            initialDelaySeconds: 5
            periodSeconds: 10

          resources:

            requests:
              cpu: 25m
              memory: 32Mi

            limits:
              cpu: 100m
              memory: 64Mi

      volumes:

        - name: html

          configMap:
            name: web2-html


---
apiVersion: v1
kind: Service

metadata:
  name: web2-service
  namespace: web2

spec:

  selector:
    app: web2

  ports:

    - name: http
      port: 80
      targetPort: 80

  type: ClusterIP
'''
                )
            }
        }


        // ============================================================
        // HAPROXY
        // ============================================================

        stage('Gerar HAProxy') {

            steps {

                writeFile(
                    file: "${env.MANIFEST_DIR}/40-haproxy.yaml",
                    text: '''
apiVersion: v1
kind: ConfigMap

metadata:
  name: haproxy-config
  namespace: gateway

data:

  haproxy.cfg: |

    global
        log stdout format raw local0
        maxconn 2000

    defaults

        log global

        mode http

        option httplog
        option dontlognull

        timeout connect 5s
        timeout client 30s
        timeout server 30s


    frontend http_front

        bind *:8080

        # ==========================================
        # Identificação das aplicações
        # ==========================================

        acl route_web1 path_reg ^/web1(/|$)
        acl route_web2 path_reg ^/web2(/|$)

        # ==========================================
        # Seleção dos backends
        # ==========================================

        use_backend backend_web1 if route_web1
        use_backend backend_web2 if route_web2

        # Qualquer outra URL vai para o Portal

        default_backend backend_portal


    # ==========================================
    # PORTAL
    # ==========================================

    backend backend_portal

        balance roundrobin

        server portal portal-service.portal.svc.cluster.local:80 check


    # ==========================================
    # WEB1
    # ==========================================

    backend backend_web1

        balance roundrobin

        # Retira /web1 da URL antes de enviar
        # para a aplicação

        http-request replace-path ^/web1/?(.*)$ /\\1

        server web1 web1-service.web1.svc.cluster.local:80 check


    # ==========================================
    # WEB2
    # ==========================================

    backend backend_web2

        balance roundrobin

        # Retira /web2 da URL antes de enviar
        # para a aplicação

        http-request replace-path ^/web2/?(.*)$ /\\1

        server web2 web2-service.web2.svc.cluster.local:80 check


---
apiVersion: apps/v1
kind: Deployment

metadata:
  name: haproxy
  namespace: gateway

spec:

  replicas: 1

  selector:

    matchLabels:
      app: haproxy

  template:

    metadata:

      labels:
        app: haproxy

    spec:

      containers:

        - name: haproxy

          image: haproxy:alpine

          ports:

            - name: http
              containerPort: 8080

          volumeMounts:

            - name: haproxy-config
              mountPath: /usr/local/etc/haproxy/haproxy.cfg
              subPath: haproxy.cfg

          readinessProbe:

            tcpSocket:
              port: 8080

            initialDelaySeconds: 2
            periodSeconds: 5

          livenessProbe:

            tcpSocket:
              port: 8080

            initialDelaySeconds: 5
            periodSeconds: 10

          resources:

            requests:
              cpu: 50m
              memory: 64Mi

            limits:
              cpu: 250m
              memory: 128Mi

      volumes:

        - name: haproxy-config

          configMap:
            name: haproxy-config


---
apiVersion: v1
kind: Service

metadata:
  name: haproxy-service
  namespace: gateway

spec:

  selector:
    app: haproxy

  ports:

    - name: http
      port: 80
      targetPort: 8080

  type: LoadBalancer
'''
                )
            }
        }


        // ============================================================
        // NETWORK POLICIES
        // ============================================================

        stage('Gerar NetworkPolicy') {

            steps {

                writeFile(
                    file: "${env.MANIFEST_DIR}/50-networkpolicy.yaml",
                    text: '''
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy

metadata:
  name: allow-gateway
  namespace: portal

spec:

  podSelector:

    matchLabels:
      app: portal

  policyTypes:
    - Ingress

  ingress:

    - from:

        - namespaceSelector:

            matchLabels:
              kubernetes.io/metadata.name: gateway

      ports:

        - protocol: TCP
          port: 80


---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy

metadata:
  name: allow-gateway
  namespace: web1

spec:

  podSelector:

    matchLabels:
      app: web1

  policyTypes:
    - Ingress

  ingress:

    - from:

        - namespaceSelector:

            matchLabels:
              kubernetes.io/metadata.name: gateway

      ports:

        - protocol: TCP
          port: 80


---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy

metadata:
  name: allow-gateway
  namespace: web2

spec:

  podSelector:

    matchLabels:
      app: web2

  policyTypes:
    - Ingress

  ingress:

    - from:

        - namespaceSelector:

            matchLabels:
              kubernetes.io/metadata.name: gateway

      ports:

        - protocol: TCP
          port: 80
'''
                )
            }
        }


        // ============================================================
        // MOSTRAR MANIFESTS
        // ============================================================

        stage('Exibir manifests') {

            steps {

                sh '''
                    echo "============================================"
                    echo "Arquivos gerados"
                    echo "============================================"

                    ls -lah "$MANIFEST_DIR"

                    echo
                    echo "============================================"
                    echo "Validando YAMLs com kubectl"
                    echo "============================================"

                    kubectl apply \
                        --dry-run=client \
                        -f "$MANIFEST_DIR/00-namespaces.yaml"

                    kubectl apply \
                        --dry-run=client \
                        -f "$MANIFEST_DIR/10-portal.yaml"

                    kubectl apply \
                        --dry-run=client \
                        -f "$MANIFEST_DIR/20-web1.yaml"

                    kubectl apply \
                        --dry-run=client \
                        -f "$MANIFEST_DIR/30-web2.yaml"

                    kubectl apply \
                        --dry-run=client \
                        -f "$MANIFEST_DIR/40-haproxy.yaml"
                '''
            }
        }


        // ============================================================
        // CRIAR NAMESPACES
        // ============================================================

        stage('Criar Namespaces') {

            steps {

                sh '''
                    set -e

                    kubectl apply \
                        -f "$MANIFEST_DIR/00-namespaces.yaml"
                '''
            }
        }


        // ============================================================
        // DEPLOY PORTAL
        // ============================================================

        stage('Deploy Portal') {

            steps {

                sh '''
                    set -e

                    kubectl apply \
                        -f "$MANIFEST_DIR/10-portal.yaml"
                '''
            }
        }


        // ============================================================
        // DEPLOY WEB1
        // ============================================================

        stage('Deploy WEB1') {

            steps {

                sh '''
                    set -e

                    kubectl apply \
                        -f "$MANIFEST_DIR/20-web1.yaml"
                '''
            }
        }


        // ============================================================
        // DEPLOY WEB2
        // ============================================================

        stage('Deploy WEB2') {

            steps {

                sh '''
                    set -e

                    kubectl apply \
                        -f "$MANIFEST_DIR/30-web2.yaml"
                '''
            }
        }


        // ============================================================
        // AGUARDAR APPS
        // ============================================================

        stage('Aguardar aplicações') {

            steps {

                sh '''
                    set -e

                    echo "Aguardando Portal..."

                    kubectl rollout status \
                        deployment/portal \
                        -n portal \
                        --timeout=120s


                    echo "Aguardando WEB1..."

                    kubectl rollout status \
                        deployment/web1 \
                        -n web1 \
                        --timeout=120s


                    echo "Aguardando WEB2..."

                    kubectl rollout status \
                        deployment/web2 \
                        -n web2 \
                        --timeout=120s
                '''
            }
        }


        // ============================================================
        // DEPLOY HAPROXY
        // ============================================================

        stage('Deploy HAProxy') {

            steps {

                sh '''
                    set -e

                    kubectl apply \
                        -f "$MANIFEST_DIR/40-haproxy.yaml"

                    kubectl rollout status \
                        deployment/haproxy \
                        -n gateway \
                        --timeout=120s
                '''
            }
        }


        // ============================================================
        // NETWORK POLICY OPCIONAL
        // ============================================================

        stage('Aplicar NetworkPolicy') {

            when {

                expression {
                    return params.APPLY_NETWORK_POLICY
                }
            }

            steps {

                sh '''
                    set -e

                    echo "Aplicando NetworkPolicies..."

                    kubectl apply \
                        -f "$MANIFEST_DIR/50-networkpolicy.yaml"
                '''
            }
        }


        // ============================================================
        // STATUS
        // ============================================================

        stage('Status Kubernetes') {

            steps {

                sh '''
                    echo
                    echo "============================================"
                    echo "NAMESPACES"
                    echo "============================================"

                    kubectl get namespace


                    echo
                    echo "============================================"
                    echo "PORTAL"
                    echo "============================================"

                    kubectl get all -n portal -o wide


                    echo
                    echo "============================================"
                    echo "WEB1"
                    echo "============================================"

                    kubectl get all -n web1 -o wide


                    echo
                    echo "============================================"
                    echo "WEB2"
                    echo "============================================"

                    kubectl get all -n web2 -o wide


                    echo
                    echo "============================================"
                    echo "GATEWAY"
                    echo "============================================"

                    kubectl get all -n gateway -o wide
                '''
            }
        }


        // ============================================================
        // TESTE INTERNO
        // ============================================================

        stage('Teste de roteamento') {

            steps {

                sh '''
                    set -e

                    TEST_POD="poc-routing-test"

                    cleanup() {
                        kubectl delete pod "$TEST_POD" \
                            -n gateway \
                            --ignore-not-found \
                            --wait=false \
                            > /dev/null 2>&1 || true
                    }

                    trap cleanup EXIT

                    cleanup


                    echo "Criando Pod temporário para teste..."

                    kubectl run "$TEST_POD" \
                        -n gateway \
                        --image=busybox:1.36 \
                        --restart=Never \
                        --command \
                        -- sleep 300


                    kubectl wait \
                        --for=condition=Ready \
                        pod/"$TEST_POD" \
                        -n gateway \
                        --timeout=60s


                    echo
                    echo "============================================"
                    echo "TESTE PORTAL"
                    echo "============================================"

                    kubectl exec \
                        -n gateway \
                        "$TEST_POD" \
                        -- wget -qO- \
                        http://haproxy-service.gateway.svc.cluster.local/ \
                        | grep "Portal de Aplicações"


                    echo
                    echo "============================================"
                    echo "TESTE WEB1"
                    echo "============================================"

                    kubectl exec \
                        -n gateway \
                        "$TEST_POD" \
                        -- wget -qO- \
                        http://haproxy-service.gateway.svc.cluster.local/web1/ \
                        | grep "Aplicação WEB 1"


                    echo
                    echo "============================================"
                    echo "TESTE WEB2"
                    echo "============================================"

                    kubectl exec \
                        -n gateway \
                        "$TEST_POD" \
                        -- wget -qO- \
                        http://haproxy-service.gateway.svc.cluster.local/web2/ \
                        | grep "Aplicação WEB 2"


                    echo
                    echo "Todos os testes de roteamento passaram."
                '''
            }
        }


        // ============================================================
        // ENDPOINT EXTERNO
        // ============================================================

        stage('Endpoint externo') {

            steps {

                sh '''
                    echo
                    echo "============================================"
                    echo "LOAD BALANCER"
                    echo "============================================"

                    kubectl get service \
                        haproxy-service \
                        -n gateway \
                        -o wide


                    EXTERNAL_IP="$(

                        kubectl get service \
                            haproxy-service \
                            -n gateway \
                            -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

                    )"


                    EXTERNAL_HOSTNAME="$(

                        kubectl get service \
                            haproxy-service \
                            -n gateway \
                            -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

                    )"


                    if [ -n "$EXTERNAL_IP" ]; then

                        echo
                        echo "Portal:"
                        echo "http://$EXTERNAL_IP/"

                        echo
                        echo "WEB1:"
                        echo "http://$EXTERNAL_IP/web1/"

                        echo
                        echo "WEB2:"
                        echo "http://$EXTERNAL_IP/web2/"

                    elif [ -n "$EXTERNAL_HOSTNAME" ]; then

                        echo
                        echo "Portal:"
                        echo "http://$EXTERNAL_HOSTNAME/"

                        echo
                        echo "WEB1:"
                        echo "http://$EXTERNAL_HOSTNAME/web1/"

                        echo
                        echo "WEB2:"
                        echo "http://$EXTERNAL_HOSTNAME/web2/"

                    else

                        echo
                        echo "O LoadBalancer ainda não recebeu endereço externo."
                        echo
                        echo "Consulte com:"
                        echo
                        echo "kubectl get svc haproxy-service -n gateway"

                    fi
                '''
            }
        }
    }


    // ================================================================
    // POST
    // ================================================================

    post {

        success {

            echo '''
============================================================
POC Kubernetes + HAProxy implantada com sucesso.
============================================================
'''
        }

        failure {

            echo '''
============================================================
A implantação apresentou erro.
Verifique os logs dos stages anteriores.
============================================================
'''

            sh '''
                echo
                echo "Pods:"
                kubectl get pods -A -o wide || true

                echo
                echo "Eventos recentes:"
                kubectl get events -A \
                    --sort-by='.lastTimestamp' \
                    | tail -50 || true
            '''
        }

        always {

            archiveArtifacts(
                artifacts: 'k8s-poc/*.yaml',
                fingerprint: true,
                allowEmptyArchive: true
            )
        }
    }
}
