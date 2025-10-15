pipeline {
    agent any

    tools {
        maven 'maven-3.8.6'
    }

    environment {
        GIT_REPO = 'https://github.com/sthuthi2002/DevSecOps-project.git'
        IMAGE_NAME = 'sthuthi2002/sprint-boot-app'
        S3_BUCKET = 'devsecops-project'
        SONARQUBE_SERVER = 'SonarQube-server' // Jenkins configured SonarQube server name
    }

    stages {

        stage('Checkout Git') {
            steps {
                git branch: 'main', url: "${GIT_REPO}"
            }
        }

        stage('Build & JUnit Test') {
            steps {
                sh 'mvn clean install'
            }
            post {
                success {
                    junit 'target/surefire-reports/**/*.xml'
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh """
                    mvn clean verify sonar:sonar \
                        -Dsonar.projectKey=devsecops-project-key \
                        -Dsonar.host.url=$SONAR_HOST_URL \
                        -Dsonar.login=$SONAR_AUTH_TOKEN
                    """
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh """
                docker build -t ${IMAGE_NAME}:v1.$BUILD_ID .
                docker tag ${IMAGE_NAME}:v1.$BUILD_ID ${IMAGE_NAME}:latest
                """
            }
        }

        stage('Image Scan with Trivy') {
            steps {
                sh """
                trivy image --format template --template "@/usr/local/share/trivy/templates/html.tpl" -o report.html ${IMAGE_NAME}:latest
                """
            }
        }

        stage('Upload Scan Report to AWS S3') {
            steps {
                sh "aws s3 cp report.html s3://${S3_BUCKET}/"
            }
        }

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
                    sh "docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD}"
                    sh "docker push ${IMAGE_NAME}:v1.$BUILD_ID"
                    sh "docker push ${IMAGE_NAME}:latest"
                    sh "docker rmi ${IMAGE_NAME}:v1.$BUILD_ID ${IMAGE_NAME}:latest"
                }
            }
        }

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

    post {
        always {
            sendSlackNotification()
        }
    }
}

def sendSlackNotification() {
    def buildSummary = """Job_name: ${env.JOB_NAME}
Build_id: ${env.BUILD_ID}
Status: ${currentBuild.currentResult}
Build_url: ${BUILD_URL}
Job_url: ${JOB_URL}"""
    
    if (currentBuild.currentResult == "SUCCESS") {
        slackSend(channel: "#devops", token: 'slack-token', color: 'good', message: buildSummary)
    } else {
        slackSend(channel: "#devops", token: 'slack-token', color: 'danger', message: buildSummary)
    }
}
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

stage('OWASP ZAP Scan') {
    steps {
        sh """
        docker run --rm --network host ghcr.io/zaproxy/zap-stable:latest \
        zap-baseline.py -t http://localhost:8080 -J zap-report.json || true
        """
    }
}

stage('Generate Security HTML Report') {
    steps {
        sh 'python3 scripts/generate-simple-report.py'
    }
}

stage('Upload HTML Report to S3') {
    steps {
        sh "aws s3 cp security-report.html s3://${S3_BUCKET}/"
    }
}
