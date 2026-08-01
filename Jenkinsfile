pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
       
        COMPOSE_PROJECT_NAME = 'ecommerce-website'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Detect Changed Services') {
            steps {
                script {
                    
                    def lastCommitFile = '/opt/fieldstead/last_deployed_commit'
                    def baseCommit = (sh(script: "test -f ${lastCommitFile}", returnStatus: true) == 0)
                        ? sh(script: "cat ${lastCommitFile}", returnStdout: true).trim()
                        : sh(script: 'git rev-list --max-parents=0 HEAD', returnStdout: true).trim()

                    def changedFiles = sh(
                        script: "git diff --name-only ${baseCommit} HEAD || true",
                        returnStdout: true
                    ).trim()

                    echo "Changed Files:"
                    echo changedFiles

                    def services = []

                    changedFiles.split("\n").each { file ->
                        // path prefixes match this repo's actual folder layout
                        if (file.startsWith("frontend/"))                 { services.add("frontend") }
                        if (file.startsWith("api-gateway/"))               { services.add("api-gateway") }
                        if (file.startsWith("services/auth-service/"))    { services.add("auth-service") }
                        if (file.startsWith("services/product-service/")) { services.add("product-service") }
                        if (file.startsWith("services/cart-service/"))    { services.add("cart-service") }
                        if (file.startsWith("services/order-service/"))  { services.add("order-service") }
                    }

                    services = services.unique()
                    env.CHANGED_SERVICES = services.join(",")
                    env.SKIP_DEPLOY = services.isEmpty() ? "true" : "false"

                    echo "Changed Services: ${env.CHANGED_SERVICES ?: '(none)'}"
                }
            }
        }

        stage('Build Changed Services') {
            when { expression { env.SKIP_DEPLOY == 'false' } }
            steps {
                script {
                    env.CHANGED_SERVICES.split(",").each { service ->
                        echo "Building ${service}"
                        sh "docker compose -p ${env.COMPOSE_PROJECT_NAME} build ${service}"
                    }
                }
            }
        }

        stage('Deploy Changed Services') {
            when { expression { env.SKIP_DEPLOY == 'false' } }
            steps {
                script {
                    env.CHANGED_SERVICES.split(",").each { service ->
                        echo "Deploying ${service}"
                        sh "docker compose -p ${env.COMPOSE_PROJECT_NAME} up -d --no-deps ${service}"
                    }
                }
            }
        }

        stage('Verify Containers') {
            when { expression { env.SKIP_DEPLOY == 'false' } }
            steps {
                script {
                    // compose service name -> actual container_name in docker-compose.yml
                    def containerName = [
                        'auth-service'   : 'fieldstead-auth',
                        'product-service': 'fieldstead-products',
                        'cart-service'   : 'fieldstead-cart',
                        'order-service'  : 'fieldstead-orders',
                        'api-gateway'    : 'fieldstead-gateway',
                        'frontend'       : 'fieldstead-frontend',
                    ]
                    env.CHANGED_SERVICES.split(",").each { service ->
                        def name = containerName[service]
                        echo "Verifying ${name}"
                        sh "docker ps --filter name=${name} --format 'table {{.Names}}\\t{{.Status}}'"
                    }
                }
            }
        }

        stage('Health Check') {
            when { expression { env.SKIP_DEPLOY == 'false' } }
            steps {
                script {
                    def containerName = [
                        'auth-service'   : 'fieldstead-auth',
                        'product-service': 'fieldstead-products',
                        'cart-service'   : 'fieldstead-cart',
                        'order-service'  : 'fieldstead-orders',
                        'api-gateway'    : 'fieldstead-gateway',
                        'frontend'       : 'fieldstead-frontend',
                    ]
                    // internal port + health path per service (frontend has no
                    // /health route, so it's checked on "/" instead)
                    def healthPath = [
                        'auth-service'   : [4001, '/health'],
                        'product-service': [4002, '/health'],
                        'cart-service'   : [4003, '/health'],
                        'order-service'  : [4004, '/health'],
                        'api-gateway'    : [4000, '/health'],
                        'frontend'       : [3000, '/'],
                    ]

                    env.CHANGED_SERVICES.split(",").each { service ->
                        def name = containerName[service]
                        def (port, path) = healthPath[service]

                        echo "Checking container: ${name}"
                        sh """
                            sleep 5
                            docker inspect --format='{{.State.Running}}' ${name}
                        """

                        // Real functional check, not just "process is running" —
                        // every image here is python:3.12-slim, so urllib from
                        // the stdlib is always available, no extra tools needed.
                        echo "Functional health check: ${name}:${port}${path}"
                        sh """
                            docker exec ${name} python -c "import urllib.request; urllib.request.urlopen('http://localhost:${port}${path}', timeout=5)"
                        """
                    }
                }
            }
        }

        stage('Record deployed commit') {
            when { expression { env.SKIP_DEPLOY == 'false' } }
            steps {
                sh 'git rev-parse HEAD > /opt/fieldstead/last_deployed_commit'
            }
        }
    }

    post {

        success {
            script {
                if (env.SKIP_DEPLOY == 'true') {
                    echo "No service changes detected — nothing deployed."
                } else {
                    echo """
=================================
Deployment Successful
=================================

Updated Services:

${env.CHANGED_SERVICES}

=================================
"""
                }
            }
        }

        failure {
            echo """
=================================
Deployment Failed
=================================

Check Jenkins logs.

=================================
"""
        }
    }
}
