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
        booleanParam(name: 'ENABLE_PERIODIC_ARTIFACT_PURGE', defaultValue: true, description: 'Every N builds, delete archived artifacts from previous builds.')
        string(name: 'PERIODIC_PURGE_EVERY', defaultValue: '5', description: 'Run full artifact purge every N-th build (integer >= 2).')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '5'))
    }

    environment {
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PYTHONUNBUFFERED = '1'
        PLAYWRIGHT_BROWSERS_PATH = "${JENKINS_HOME}\\cache\\ms-playwright"
        PIP_CACHE_DIR = "${JENKINS_HOME}\\cache\\pip"
        PYTHON_BIN_FILE = '.python_bin'
        REQ_HASH_FILE = '.requirements.sha256'
    }

    stages {
        stage('Prepare') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"
                    $reqHashFile = $env:REQ_HASH_FILE

                    Write-Host "=== Cache diagnostics ==="
                    Write-Host "Workspace: $(Get-Location)"
                    Write-Host "JENKINS_HOME: $env:JENKINS_HOME"
                    Write-Host "PLAYWRIGHT_BROWSERS_PATH: $env:PLAYWRIGHT_BROWSERS_PATH"
                    Write-Host "PIP_CACHE_DIR: $env:PIP_CACHE_DIR"

                    if (Test-Path ".\\.venv\\Scripts\\python.exe") {
                        Write-Host "[VENV] Reused: .venv exists"
                        & .\\.venv\\Scripts\\python.exe --version
                    } else {
                        Write-Host "[VENV] Missing: .venv will be created"
                    }

                    if (Test-Path $reqHashFile) {
                        Write-Host "[REQ_HASH] Found: $(Get-Content $reqHashFile -Raw)"
                    } else {
                        Write-Host "[REQ_HASH] Missing: deps install expected"
                    }

                    if (Test-Path $env:PIP_CACHE_DIR) {
                        Write-Host "[PIP_CACHE] Found: $env:PIP_CACHE_DIR"
                    } else {
                        Write-Host "[PIP_CACHE] Missing: $env:PIP_CACHE_DIR"
                    }

                    if (Test-Path $env:PLAYWRIGHT_BROWSERS_PATH) {
                        Write-Host "[PW_CACHE] Found: $env:PLAYWRIGHT_BROWSERS_PATH"
                    } else {
                        Write-Host "[PW_CACHE] Missing: $env:PLAYWRIGHT_BROWSERS_PATH"
                    }
                    Write-Host "========================="

                    New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR | Out-Null
                    New-Item -ItemType Directory -Force -Path $env:PLAYWRIGHT_BROWSERS_PATH | Out-Null

                    $pythonBin = ".\\.venv\\Scripts\\python.exe"
                    if (-not (Test-Path $pythonBin)) {
                        python -m venv .venv
                    }

                    if (-not (Test-Path $pythonBin)) {
                        python -m ensurepip --upgrade
                        python -m venv .venv
                    }

                    if (-not (Test-Path $pythonBin)) {
                        throw "Unable to create .venv"
                    }

                    Set-Content -Path $env:PYTHON_BIN_FILE -Value $pythonBin -NoNewline
                    & $pythonBin --version

                    $currentHash = (Get-FileHash -Path requirements.txt -Algorithm SHA256).Hash
                    $savedHash = ""
                    if (Test-Path $reqHashFile) {
                        $savedHash = (Get-Content $reqHashFile -Raw).Trim()
                    }

                    $needInstall = $false
                    if (-not (Test-Path $reqHashFile)) {
                        $needInstall = $true
                    }
                    if ($currentHash -ne $savedHash) {
                        $needInstall = $true
                    }

                    & $pythonBin -m pytest --version | Out-Null
                    if ($LASTEXITCODE -ne 0) {
                        $needInstall = $true
                    }

                    if ($needInstall) {
                        Write-Host "Installing Python dependencies (first run or requirements changed)..."
                        & $pythonBin -m pip install --cache-dir $env:PIP_CACHE_DIR --upgrade pip
                        & $pythonBin -m pip install --cache-dir $env:PIP_CACHE_DIR -r requirements.txt
                        Set-Content -Path $reqHashFile -Value $currentHash -NoNewline
                    } else {
                        Write-Host "Python dependencies already installed, skip pip install."
                    }

                    $chromiumCache = Get-ChildItem -Path $env:PLAYWRIGHT_BROWSERS_PATH -Directory -Filter 'chromium-*' -ErrorAction SilentlyContinue
                    if (-not $chromiumCache) {
                        & $pythonBin -m playwright install chromium
                    } else {
                        Write-Host "Chromium already exists in shared cache."
                    }
                '''
            }
        }

        stage('Run') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"
                    $pythonBin = ".\\.venv\\Scripts\\python.exe"
                    if (Test-Path $env:PYTHON_BIN_FILE) {
                        $pythonBin = (Get-Content $env:PYTHON_BIN_FILE -Raw).Trim()
                    }

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
                    & $pythonBin @pytestArgs
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/*.xlsx,artifacts/**/*', allowEmptyArchive: true
            powershell '''
                $ErrorActionPreference = "SilentlyContinue"
                Remove-Item -Recurse -Force artifacts, .pytest_cache, pytest-cache-files-*, __pycache__ -ErrorAction SilentlyContinue
            '''
            script {
                if (params.ENABLE_PERIODIC_ARTIFACT_PURGE) {
                    powershell '''
                        $ErrorActionPreference = "SilentlyContinue"

                        $parsedPurgeEvery = 5
                        if (-not [int]::TryParse($env:PERIODIC_PURGE_EVERY, [ref]$parsedPurgeEvery) -or $parsedPurgeEvery -lt 2) {
                            $parsedPurgeEvery = 5
                        }

                        $parsedBuildNumber = 0
                        if (-not [int]::TryParse($env:BUILD_NUMBER, [ref]$parsedBuildNumber)) {
                            Write-Host "[PURGE] BUILD_NUMBER is not numeric, skip."
                            exit 0
                        }

                        $buildNumber = $parsedBuildNumber
                        if (($buildNumber % $parsedPurgeEvery) -ne 0) {
                            Write-Host "[PURGE] Skip: build #$buildNumber is not each $parsedPurgeEvery-th run."
                            exit 0
                        }

                        if (-not $env:JENKINS_HOME -or -not $env:JOB_NAME) {
                            Write-Host "[PURGE] JENKINS_HOME or JOB_NAME is empty, skip."
                            exit 0
                        }

                        $jobPath = ($env:JOB_NAME -split '/' | ForEach-Object { "jobs\\$_" }) -join '\'
                        $buildsDir = Join-Path $env:JENKINS_HOME (Join-Path $jobPath 'builds')
                        if (-not (Test-Path $buildsDir)) {
                            Write-Host "[PURGE] Builds dir not found: $buildsDir"
                            exit 0
                        }

                        Write-Host "[PURGE] Running periodic purge for $env:JOB_NAME at build #$buildNumber (every $parsedPurgeEvery)"
                        Get-ChildItem -Path $buildsDir -Directory | Where-Object { $_.Name -ne $env:BUILD_NUMBER } | ForEach-Object {
                            $archiveDir = Join-Path $_.FullName 'archive'
                            $allureDir = Join-Path $_.FullName 'allure-report'
                            if (Test-Path $archiveDir) {
                                Remove-Item -LiteralPath $archiveDir -Recurse -Force
                            }
                            if (Test-Path $allureDir) {
                                Remove-Item -LiteralPath $allureDir -Recurse -Force
                            }
                        }
                        Write-Host "[PURGE] Done."
                    '''
                } else {
                    echo 'Periodic artifact purge disabled by parameter.'
                }
            }
        }
    }
}
