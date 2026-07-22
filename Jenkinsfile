// Declarative Pipeline — kod push'unda otomatik: test → imaj build → push → deploy.
// Jenkins bu dosyayı deponun kökünden okur ("Pipeline script from SCM").

pipeline {
    // Nerede çalışsın: "any" → uygun herhangi bir Jenkins düğümü (bizde: Jenkins
    // konteynerinin kendisi; içinde Python ve Docker CLI kurulu).
    agent any

    // Tüm aşamalarda geçerli ortam değişkenleri.
    environment {
        REGISTRY = 'ghcr.io'
        IMAGE    = 'ghcr.io/enesalptuman/donati-tarama-arayuz'
    }

    options {
        timestamps()                 // her log satırına zaman damgası
        disableConcurrentBuilds()    // aynı anda iki build çalışmasın (deploy çakışması olmasın)
    }

    // Tetikleme: Jenkins GitHub'ı ~2 dakikada bir yoklar; yeni commit varsa build eder.
    // (Yerel Jenkins'e GitHub webhook ulaşamadığı için polling kullanıyoruz.)
    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {
        // 1) Kaynağı çek (Jenkins job'ında tanımlı depo/branch'ten).
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // 2) Bağımlılıkları izole bir venv'e kur (çalışma + geliştirme).
        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt -r requirements-dev.txt
                '''
            }
        }

        // 3) Kod kalitesi: ruff temiz değilse pipeline burada durur.
        stage('Lint') {
            steps {
                sh '. .venv/bin/activate && ruff check .'
            }
        }

        // 4) Testler + coverage. Bir test bile kırılırsa pipeline durur (deploy olmaz).
        stage('Test') {
            steps {
                sh '. .venv/bin/activate && pytest --cov=app'
            }
        }

        // 5) Docker imajını derle ve iki etiketle işaretle: build numarası + latest.
        stage('Docker Build') {
            steps {
                sh "docker build -t ${IMAGE}:${BUILD_NUMBER} -t ${IMAGE}:latest ."
            }
        }

        // 6) İmajı ghcr.io'ya gönder. Sadece main branch'te ve kimlik bilgisiyle.
        stage('Push') {
            when { branch 'main' }
            environment {
                // Jenkins'te tanımlı 'github-pat' (GitHub kullanıcı adı + PAT) →
                // otomatik GHCR_USR ve GHCR_PSW değişkenlerine ayrışır.
                // Aynı kimlik hem private repo klonlama hem ghcr push için kullanılır.
                GHCR = credentials('github-pat')
            }
            steps {
                sh 'echo "$GHCR_PSW" | docker login ghcr.io -u "$GHCR_USR" --password-stdin'
                sh "docker push ${IMAGE}:${BUILD_NUMBER}"
                sh "docker push ${IMAGE}:latest"
            }
        }

        // 7) Deploy (yerel demo): compose ile app + postgres'i ayağa kaldır.
        //    Faz 5'te bu aşama uzak sunucuya SSH ile deploy edecek şekilde değişecek.
        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh 'docker compose -p donati up -d'
            }
        }
    }

    // Aşamalardan SONRA, sonuca göre çalışan bloklar.
    post {
        success {
            echo '✅ Pipeline başarılı — test geçti, imaj build/push edildi, deploy tamam.'
        }
        failure {
            echo '❌ Pipeline BAŞARISIZ — yukarıdaki aşama loglarını inceleyin.'
        }
        always {
            // Çalışma alanı temizliği (venv'i bırakma).
            sh 'rm -rf .venv || true'
        }
    }
}
