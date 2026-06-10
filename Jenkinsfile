pipeline {
    agent any

    triggers {
        cron('H H * * 1')
    }

    parameters {
        choice(name: 'TARGET', choices: ['all', 'domain', 'url'], description: 'Scope of execution')
        string(name: 'DOMAIN', defaultValue: '', description: 'Domain filter for TARGET=domain')
        string(name: 'URL', defaultValue: '', description: 'Single landing URL for TARGET=url')
        choice(name: 'RUN_MODE', choices: ['pilot', 'release'], description: 'Pilot does not fail build on product errors')
        booleanParam(name: 'HEADLESS', defaultValue: true, description: 'Run browser in headless mode')
        choice(name: 'TRACE', choices: ['off', 'retain-on-failure', 'on'], description: 'Playwright trace mode')
        choice(name: 'SCREENSHOT', choices: ['off', 'only-on-failure', 'on'], description: 'Screenshot mode')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    stages {
        stage('Install') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"
                    python -m pip install -r requirements.txt
                    python -m playwright install chromium
                '''
            }
        }

        stage('Run') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"
                    $pytestArgs = @(
                        "-m", "pytest",
                        "--target", $env:TARGET,
                        "--run-mode", $env:RUN_MODE,
                        "--playwright-trace", $env:TRACE,
                        "--screenshot", $env:SCREENSHOT
                    )
                    if ($env:DOMAIN) {
                        $pytestArgs += @("--domain", $env:DOMAIN)
                    }
                    if ($env:URL) {
                        $pytestArgs += @("--url", $env:URL)
                    }
                    if ($env:HEADLESS -eq "false") {
                        $pytestArgs += "--headed"
                    }
                    python @pytestArgs
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/*.xlsx,artifacts/**/*', allowEmptyArchive: true
        }
    }
}
