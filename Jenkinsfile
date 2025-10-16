pipeline {
  agent any

  environment {
    IMAGE_NAME = 'devsecops-demo'
    SONAR_TOKEN = credentials('sonar-token') // Jenkins credential
  }

  stages {

    /* --- Stage 1: Checkout --- */
    stage('Checkout') {
      steps { 
        checkout scm 
      }
    }

    /* --- Stage 2: Build & Test --- */
    stage('Build & Test') {
      steps {
        sh 'echo "Run unit tests (if any)"; true'
        // For Node: sh 'npm install && npm test'
        // For Java: sh 'mvn clean test'
      }
    }

    /* --- Stage 3: SAST - SonarQube --- */
    stage('SAST - SonarQube') {
      steps {
        withSonarQubeEnv('SonarQube') {
          sh """
            docker run --rm \
              -v "\${PWD}:/usr/src" \
              -e SONAR_HOST_URL="http://host.docker.internal:9000" \
              -e SONAR_LOGIN=\${SONAR_TOKEN} \
              sonarsource/sonar-scanner-cli \
              -Dsonar.projectKey=devsecops-demo \
              -Dsonar.sources=/usr/src
          """
        }
      }
    }

    /* --- Stage 4: Quality Gate --- */
    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    /* --- Stage 5: Build Docker Image --- */
    stage('Build Docker Image') {
      steps {
        sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
        sh "docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest || true"
      }
    }

    /* --- Stage 6: Container Security Scan (Trivy) --- */
    stage('Container Security Scan') {
      steps {
        sh """
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
          aquasec/trivy:latest image \
          --format json --output trivy-report.json \
          ${IMAGE_NAME}:${BUILD_NUMBER} || true
        """
        archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
      }
    }

    /* --- Stage 7: Security Gate Check --- */
    stage('Security Gate Check') {
      steps {
        script {
          def trivy = readJSON file: 'trivy-report.json'
          def critical = 0
          trivy.Results.each { r ->
            (r.Vulnerabilities ?: []).each { v ->
              if (v.Severity == 'CRITICAL') critical++
            }
          }
          if (critical > 0) {
            error "Security Gate Failed: ${critical} CRITICAL vulnerabilities found"
          } else {
            echo "Security Gate Passed: No CRITICAL vulnerabilities"
          }
        }
      }
    }

    /* --- Stage 8: Deploy to Staging (Kubernetes) --- */
    stage('Deploy to Staging') {
      steps {
        sh """
          kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
          kubectl apply -f k8s/staging/ -n staging
          kubectl set image deployment/app app=${IMAGE_NAME}:${BUILD_NUMBER} -n staging || true
          kubectl rollout status deployment/app -n staging
        """
      }
    }

    /* --- Stage 9: DAST - OWASP ZAP --- */
    stage('DAST - ZAP') {
      steps {
        script {
          // Get Minikube IP dynamically
          def minikubeIp = sh(script: "minikube ip", returnStdout: true).trim()

          sh """
            docker run --rm -v \$PWD:/zap/wrk:Z --network host \
            owasp/zap2docker-stable \
            zap-baseline.py -t http://${minikubeIp}:30000 \
            -J /zap/wrk/zap-report.json \
            -r /zap/wrk/zap-report.html || true
          """
        }
        archiveArtifacts artifacts: 'zap-report.json,zap-report.html', allowEmptyArchive: true
      }
    }

  }

  post {
    always {
      // Generate simple HTML report
      sh 'python3 scripts/generate-simple-report.py || true'
      archiveArtifacts artifacts: 'security-report.html', allowEmptyArchive: true
    }
  }
}
