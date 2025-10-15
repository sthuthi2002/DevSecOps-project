pipeline {
    agent any

    tools {
        maven 'maven-3.8.6'
    }

    environment {
        GIT_REPO = 'https://github.com/sthuthi2002/DevSecOps-project.git'
        IMAGE_NAME = 'sthuthi2002/spring-boot-app'
        S3_BUCKET = 'devsecops-project'
        SONARQUBE_SERVER = 'SonarQube-server' // Jenkins → Configure System → SonarQube installations
    }

    stages {

        /* --- Stage 1: Checkout --- */
        stage('Checkout') {
            steps {
                git branch: 'main', url: "${GIT_REPO}"
            }
        }

        /* --- Stage 2: Build & Test --- */
        stage('Build & Test') {
            steps {
                sh 'mvn clean install'
            }
            post {
                success {
                    junit 'target/surefire-reports/**/*.xml'
                }
            }
        }

        /* --- Stage 3: SonarQube Analysis --- */
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh """
                        mvn clean verify sonar:sonar \
                            -Dsonar.projectKey=devsecops-project \
                            -Dsonar.host.url=$SONAR_HOST_URL \
                            -Dsonar.login=$SONAR_AUTH_TOKEN
                    """
                }
            }
        }

        /* --- Stage 4: Quality Gate --- */
        stage('Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        /* --- Stage 5: Docker Build --- */
        stage('Docker Build') {
            steps {
                sh """
                    docker build -t ${IMAGE_NAME}:v1.${BUILD_ID} .
                    docker tag ${IMAGE_NAME}:v1.${BUILD_ID} ${IMAGE_NAME}:latest
                """
            }
        }

        /* --- Stage 6: Trivy Scan --- */
        stage('Trivy Scan') {
            steps {
                sh """
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                    aquasec/trivy:latest image \
                    --severity HIGH,CRITICAL \
                    --format json \
                    --output trivy-report.json \
                    ${IMAGE_NAME}:latest
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

        /* --- Stage 8: Upload Reports --- */
        stage('Upload Scan Reports to S3') {
            steps {
                sh """
                    aws s3 cp trivy-report.json s3://${S3_BUCKET}/
                    aws s3 cp zap-report.json s3://${S3_BUCKET}/
                """
            }
        }

        /* --- Stage 9: Docker Push --- */
        stage('Docker Push') {
            steps {
                withVault(
                    configuration: [
                        skipSslVerification: true,
                        timeout: 60,
                        vaultCredentialId: 'vault-cred',
                        vaultUrl: 'http://your-vault-server-ip:8200'
                    ],
                    vaultSecrets: [
                        [path: 'secret/docker', secretValues: [
                            [envVar: 'DOCKER_USERNAME', vaultKey: 'username'],
                            [envVar: 'DOCKER_PASSWORD', vaultKey: 'password']
                        ]]
                    ]
                ) {
                    sh """
                        docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD}
                        docker push ${IMAGE_NAME}:v1.${BUILD_ID}
                        docker push ${IMAGE_NAME}:latest
                        docker rmi ${IMAGE_NAME}:v1.${BUILD_ID} ${IMAGE_NAME}:latest
                    """
                }
            }
        }

        /* --- Stage 10: Deploy to Kubernetes --- */
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    kubernetesDeploy(
                        configs: 'k8s/staging/deployment.yaml',
                        kubeconfigId: 'kubernetes'
                    )
                }
            }
        }
    }

    /* --- Notifications --- */
    post {
        always {
            script {
                try {
                    sendSlackNotification()
                } catch (err) {
                    echo "Slack notification failed: ${err}"
                }
            }
        }
    }
}

/* --- Slack Notification Function --- */
def sendSlackNotification() {
    def buildSummary = """\
*Job Name:* ${env.JOB_NAME}
*Build ID:* ${env.BUILD_ID}
*Status:* ${currentBuild.currentResult}
*Build URL:* ${BUILD_URL}
"""

    def color = (currentBuild.currentResult == "SUCCESS") ? 'good' : 'danger'

    // Use Jenkins Credential ID for Slack token
    withCredentials([string(credentialsId: 'slack-token-id', variable: 'SLACK_TOKEN')]) {
        slackSend(channel: '#devops', token: SLACK_TOKEN, color: color, message: buildSummary)
    }
}

