pipeline {
    agent any

    stages {
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

        stage('Validar manifests') {
            steps {
                sh '''
                    set -e

                    kubectl apply --dry-run=client -f k8s/base/namespaces.yaml

                    kubectl apply --dry-run=client -f k8s/portal/configmap.yaml
                    kubectl apply --dry-run=client -f k8s/portal/deployment.yaml
                    kubectl apply --dry-run=client -f k8s/portal/service.yaml

                    kubectl apply --dry-run=client -f k8s/web1/configmap.yaml
                    kubectl apply --dry-run=client -f k8s/web1/deployment.yaml
                    kubectl apply --dry-run=client -f k8s/web1/service.yaml

                    kubectl apply --dry-run=client -f k8s/web2/configmap.yaml
                    kubectl apply --dry-run=client -f k8s/web2/deployment.yaml
                    kubectl apply --dry-run=client -f k8s/web2/service.yaml

                    kubectl apply --dry-run=client -f k8s/gateway/configmap.yaml
                    kubectl apply --dry-run=client -f k8s/gateway/deployment.yaml
                    kubectl apply --dry-run=client -f k8s/gateway/service.yaml
                '''
            }
        }

        stage('Criar Namespaces') {
            steps {
                sh '''
                    set -e
                    kubectl apply -f k8s/base/namespaces.yaml
                '''
            }
        }

        stage('Deploy Portal') {
            steps {
                sh '''
                    set -e

                    kubectl apply -f k8s/portal/configmap.yaml
                    kubectl apply -f k8s/portal/deployment.yaml
                    kubectl apply -f k8s/portal/service.yaml

                    /* groovylint-disable-next-line LineLength */
                    kubectl rollout status                         deployment/portal                         -n portal                         --timeout=120s
                '''
            }
        }

        stage('Deploy WEB1') {
            steps {
                sh '''
                    set -e

                    kubectl apply -f k8s/web1/configmap.yaml
                    kubectl apply -f k8s/web1/deployment.yaml
                    kubectl apply -f k8s/web1/service.yaml

                    /* groovylint-disable-next-line LineLength */
                    kubectl rollout status deployment/web1 -n web1 --timeout=120s
                '''
            }
        }

        stage('Deploy WEB2') {
            steps {
                sh '''
                    set -e

                    kubectl apply -f k8s/web2/configmap.yaml
                    kubectl apply -f k8s/web2/deployment.yaml
                    kubectl apply -f k8s/web2/service.yaml

                    /* groovylint-disable-next-line LineLength */
                    kubectl rollout status                         deployment/web2                         -n web2                         --timeout=120s
                '''
            }
        }

        stage('Deploy HAProxy') {
            steps {
                sh '''
                    set -e

                    kubectl apply -f k8s/gateway/configmap.yaml
                    kubectl apply -f k8s/gateway/deployment.yaml
                    kubectl apply -f k8s/gateway/service.yaml

                    /* groovylint-disable-next-line LineLength */
                    kubectl rollout status deployment/haproxy -n gateway --timeout=120s
                '''
            }
        }   
        stage('Teste de roteamento') {
            steps {
                sh '''
                    set -e

                    TEST_POD="poc-routing-test"

                    cleanup() {
                        kubectl delete pod "$TEST_POD"                             -n gateway                             --ignore-not-found                             --wait=false                             >/dev/null 2>&1 || true
                    }

                    trap cleanup EXIT
                    cleanup

                    kubectl run "$TEST_POD"                         -n gateway                         --image=busybox:1.36                         --restart=Never                         --command -- sleep 300

                    kubectl wait                         --for=condition=Ready                         pod/"$TEST_POD"                         -n gateway                         --timeout=60s

                    /* groovylint-disable-next-line LineLength */
                    kubectl exec -n gateway "$TEST_POD" --                         wget -qO- http://haproxy-service.gateway.svc.cluster.local/                         | grep "Portal de Aplicações"

                    /* groovylint-disable-next-line LineLength */
                    kubectl exec -n gateway "$TEST_POD" --                         wget -qO- http://haproxy-service.gateway.svc.cluster.local/web1/                         | grep "Aplicação WEB 1"

                    /* groovylint-disable-next-line LineLength */
                    kubectl exec -n gateway "$TEST_POD" --                         wget -qO- http://haproxy-service.gateway.svc.cluster.local/web2/                         | grep "Aplicação WEB 2"
                '''
            }
        }

        stage('Status') {
            steps {
                sh '''
                    echo "===== GATEWAY ====="
                    kubectl get all -n gateway -o wide

                    echo "===== PORTAL ====="
                    kubectl get all -n portal -o wide

                    echo "===== WEB1 ====="
                    kubectl get all -n web1 -o wide

                    echo "===== WEB2 ====="
                    kubectl get all -n web2 -o wide

                    echo "===== LOAD BALANCER ====="
                    kubectl get svc haproxy-service -n gateway
                '''
            }
        }
    }

    post {
        failure {
            sh '''
                kubectl get pods -A -o wide || true
                kubectl get events -A --sort-by='.lastTimestamp' | tail -50 || true
            '''
        }
    }
}
