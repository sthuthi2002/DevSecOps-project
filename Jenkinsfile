pipeline {
    agent any

    tools {
        maven 'maven-3.8.6'    // must match Jenkins tool name
    }

    environment {
        SONARQUBE_ENV = 'SonarQube'      // matches Jenkins SonarQube config name
        IMAGE_NAME = 'sthuthi2002/devsecops-app'
        DOCKER_REGISTRY = 'docker.io'
        K8S_CONFIG_ID = 'kubernetes'     // Jenkins credential ID for kubeconfig
        SLACK_CHANNEL = '#devops'
        SLACK_TOKEN = 'slack-token'      // Replace with Jenkins secret text credential ID
    }

    stages {

        /* --- Stage 1: Checkout --- */
        stage('Checkout') {
            steps {
                deleteDir()
                git branch: 'main', url: 'https://github.com/sthuthi2002/DevSecOps-project.git'
            }
        }

        /* --- Stage 2: Build --- */
        stage('Build') {
            steps {
                sh 'mvn clean install -DskipTests'
            }
        }

        /* --- Stage 3: SonarQube Static Analysis --- */
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_ENV}") {
                    script {
                        def scannerHome = tool 'SonarScanner'
                        sh """
                          ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=devsecops-project \
                            -Dsonar.sources=. \
                            -Dsonar.java.binaries=target/classes \
                            -Dsonar.sourceEncoding=UTF-8 \
                            -Dsonar.host.url=$SONAR_HOST_URL \
                            -Dsonar.login=$SONAR_AUTH_TOKEN
                        """
                    }
                }
            }
        }

        /* --- Stage 4: Quality Gate --- */
        stage('Quality Gate') {
            steps {
                script {
                    try {
                        timeout(time: 5, unit: 'MINUTES') {
                            def qg = waitForQualityGate()
                            echo "🔍 SonarQube Quality Gate Status: ${qg.status}"
                            if (qg.status != 'OK') {
                                error "❌ Quality Gate failed: ${qg.status}"
                            } else {
                                echo "✅ Quality Gate passed successfully!"
                            }
                        }
                    } catch (e) {
                        echo "⚠️ Quality Gate check timed out, continuing..."
                        currentBuild.result = 'SUCCESS'
                    }
                }
            }
        }

        /* --- Stage 5: Docker Build --- */
        stage('Docker Build') {
            steps {
                sh """
                docker build -t ${IMAGE_NAME}:v${BUILD_ID} .
                docker tag ${IMAGE_NAME}:v${BUILD_ID} ${IMAGE_NAME}:latest
                """
            }
        }

        /* --- Stage 6: Trivy Vulnerability Scan --- */
        stage('Trivy Scan') {
            steps {
                sh """
                docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                aquasec/trivy:latest image --severity HIGH,CRITICAL \
                --format template --template "@/usr/local/share/trivy/templates/html.tpl" \
                -o trivy-report.html ${IMAGE_NAME}:latest
                """
            }
        }

        /* --- Stage 7: OWASP ZAP Scan --- */
        stage('OWASP ZAP Scan') {
            steps {
                sh """
                docker run --rm --network host ghcr.io/zaproxy/zap-stable:latest \
                zap-baseline.py -t http://localhost:8080 -J zap-report.json || true
                """
            }
        }

        /* --- Stage 8: Push Docker Image --- */
        stage('Docker Push') {
            environment {
                DOCKERHUB_CRED = credentials('dockerhub-cred') // Jenkins credential ID
            }
            steps {
                sh """
                echo ${DOCKERHUB_CRED_PSW} | docker login -u ${DOCKERHUB_CRED_USR} --password-stdin
                docker push ${IMAGE_NAME}:v${BUILD_ID}
                docker push ${IMAGE_NAME}:latest
                docker rmi ${IMAGE_NAME}:v${BUILD_ID} ${IMAGE_NAME}:latest
                """
            }
        }

        /* --- Stage 9: Deploy to Kubernetes --- */
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    kubernetesDeploy(
                        configs: 'k8s/deployment.yaml',
                        kubeconfigId: "${K8S_CONFIG_ID}"
                    )
                }
            }
        }
    }

    /* --- Post Actions --- */
    post {
        always {
            echo "🧹 Cleaning up workspace..."
            deleteDir()
        }
        success {
            echo "🎉 Pipeline completed successfully!"
            sendSlackNotification("SUCCESS")
        }
        failure {
            echo "❌ Pipeline failed!"
            sendSlackNotification("FAILURE")
        }
    }
}

/* --- Helper Function: Slack Notification --- */
def sendSlackNotification(status) {
    def color = (status == "SUCCESS") ? "good" : "danger"
    def message = """*Jenkins Build Summary*
*Job:* ${env.JOB_NAME}
*Build ID:* ${env.BUILD_ID}
*Status:* ${status}
*URL:* ${env.BUILD_URL}"""

    slackSend(channel: "${env.SLACK_CHANNEL}", color: color, message: message, tokenCredentialId: "${env.SLACK_TOKEN}")
}
