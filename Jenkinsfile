pipeline {
    agent any

    triggers {
        cron('H H * * 1')
    }

    parameters {
        booleanParam(name: 'VALIDATION_ONLY', defaultValue: false, description: 'Skip browser run and validate an existing report only')
        string(name: 'INPUT_REPORT', defaultValue: '', description: 'Path to an existing first-iteration report for validation-only mode')
        choice(name: 'TARGET', choices: ['all', 'domain', 'url'], description: 'Scope of execution')
        string(name: 'DOMAIN', defaultValue: '', description: 'Domain filter for TARGET=domain')
        string(name: 'URL', defaultValue: '', description: 'Single landing URL for TARGET=url')
        choice(name: 'RUN_MODE', choices: ['pilot', 'release'], description: 'Pilot does not fail build on product errors')
        booleanParam(name: 'HEADLESS', defaultValue: true, description: 'Run browser in headless mode')
        choice(name: 'TRACE', choices: ['off', 'retain-on-failure', 'on'], description: 'Playwright trace mode')
        choice(name: 'SCREENSHOT', choices: ['off', 'only-on-failure', 'on'], description: 'Screenshot mode')
        booleanParam(name: 'USE_FINAL_URL_AS_FALLBACK', defaultValue: false, description: 'Use final URL when clicked URL is empty during validation')
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
        PLAYWRIGHT_BROWSERS_PATH = "${JENKINS_HOME}/cache/ms-playwright"
        PIP_CACHE_DIR = "${JENKINS_HOME}/cache/pip"
        PYTHON_BIN_FILE = '.python_bin'
        REQ_HASH_FILE = '.requirements.sha256'
        REFERENCE_LINKS_FILE = credentials('Links_mobile_tarriffs')
        VALIDATION_REPORT_PATH = "reports/partner_links_mobile_validated_${BUILD_NUMBER}.xlsx"
    }

    stages {
        stage('Select landing') {
            when {
                expression { return !params.VALIDATION_ONLY }
            }
            steps {
                script {
                    def landingsSource = readFile('config/landings.py')

                    def extractChoices = { String pattern ->
                        def values = []
                        def matcher = (landingsSource =~ pattern)
                        matcher.each { match ->
                            if (match.size() > 1) {
                                values << match[1]
                            }
                        }
                        return values.unique()
                    }

                    def domainChoices = extractChoices(/domain="([^"]+)"/)
                    def urlChoices = extractChoices(/url="([^"]+)"/)

                    if (env.TARGET == 'domain' && !(env.DOMAIN?.trim())) {
                        if (!domainChoices) {
                            error('No domains found in config/landings.py')
                        }
                        env.DOMAIN = input(
                            message: 'Select domain for Jenkins run',
                            ok: 'Use domain',
                            parameters: [
                                choice(
                                    name: 'DOMAIN',
                                    choices: domainChoices.join('\n')
                                )
                            ]
                        )
                    }

                    if (env.TARGET == 'url' && !(env.URL?.trim())) {
                        if (!urlChoices) {
                            error('No URLs found in config/landings.py')
                        }
                        env.URL = input(
                            message: 'Select landing URL for Jenkins run',
                            ok: 'Use URL',
                            parameters: [
                                choice(
                                    name: 'URL',
                                    choices: urlChoices.join('\n')
                                )
                            ]
                        )
                    }
                }
            }
        }

        stage('Prepare') {
            steps {
                sh '''#!/usr/bin/env bash
set -euo pipefail

req_hash_file="${REQ_HASH_FILE}"
python_bin="python3"
if ! command -v python3 >/dev/null 2>&1; then
  python_bin="python"
fi

echo "=== Cache diagnostics ==="
echo "Workspace: $(pwd)"
echo "JENKINS_HOME: ${JENKINS_HOME:-}"
echo "PLAYWRIGHT_BROWSERS_PATH: ${PLAYWRIGHT_BROWSERS_PATH}"
echo "PIP_CACHE_DIR: ${PIP_CACHE_DIR}"

if [ -x ".venv/bin/python" ]; then
  echo "[VENV] Reused: .venv exists"
  .venv/bin/python --version
else
  echo "[VENV] Missing: .venv will be created"
fi

if [ -f "$req_hash_file" ]; then
  echo "[REQ_HASH] Found: $(cat "$req_hash_file")"
else
  echo "[REQ_HASH] Missing: deps install expected"
fi

if [ -d "$PIP_CACHE_DIR" ]; then
  echo "[PIP_CACHE] Found: $PIP_CACHE_DIR"
else
  echo "[PIP_CACHE] Missing: $PIP_CACHE_DIR"
fi

if [ -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
  echo "[PW_CACHE] Found: $PLAYWRIGHT_BROWSERS_PATH"
else
  echo "[PW_CACHE] Missing: $PLAYWRIGHT_BROWSERS_PATH"
fi
echo "========================="

mkdir -p "$PIP_CACHE_DIR" "$PLAYWRIGHT_BROWSERS_PATH"

if [ ! -x ".venv/bin/python" ]; then
  "$python_bin" -m venv .venv
fi

if [ ! -x ".venv/bin/python" ]; then
  "$python_bin" -m ensurepip --upgrade || true
  "$python_bin" -m venv .venv
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Unable to create .venv"
  exit 1
fi

python_bin=".venv/bin/python"
printf '%s' "$python_bin" > "$PYTHON_BIN_FILE"
"$python_bin" --version

current_hash="$(sha256sum requirements.txt | awk '{print $1}')"
saved_hash=""
if [ -f "$req_hash_file" ]; then
  saved_hash="$(tr -d '\r\n' < "$req_hash_file")"
fi

need_install=0
if [ ! -f "$req_hash_file" ]; then
  need_install=1
fi
if [ "$current_hash" != "$saved_hash" ]; then
  need_install=1
fi
if ! "$python_bin" -m pytest --version >/dev/null 2>&1; then
  need_install=1
fi

if [ "$need_install" -eq 1 ]; then
  echo "Installing Python dependencies (first run or requirements changed)..."
  "$python_bin" -m pip install --cache-dir "$PIP_CACHE_DIR" --upgrade pip
  "$python_bin" -m pip install --cache-dir "$PIP_CACHE_DIR" -r requirements.txt
  printf '%s' "$current_hash" > "$req_hash_file"
else
  echo "Python dependencies already installed, skip pip install."
fi

if ! ls "$PLAYWRIGHT_BROWSERS_PATH"/chromium-* >/dev/null 2>&1; then
  "$python_bin" -m playwright install chromium
else
  echo "Chromium already exists in shared cache."
fi
'''
            }
        }

        stage('Collect actual links') {
            when {
                expression { return !params.VALIDATION_ONLY }
            }
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    sh '''#!/usr/bin/env bash
set -euo pipefail

python_bin="python3"
if [ -f "$PYTHON_BIN_FILE" ]; then
  python_bin="$(tr -d '\r\n' < "$PYTHON_BIN_FILE")"
fi
if [ ! -x "$python_bin" ]; then
  python_bin=".venv/bin/python"
fi

pytest_args=(
  -m pytest
  --target "$TARGET"
  --run-mode "$RUN_MODE"
  --playwright-trace "$TRACE"
  --screenshot "$SCREENSHOT"
)

if [ -n "${DOMAIN:-}" ]; then
  pytest_args+=( --domain "$DOMAIN" )
fi
if [ -n "${URL:-}" ]; then
  pytest_args+=( --url "$URL" )
fi
if [ "${HEADLESS}" = "false" ]; then
  pytest_args+=( --headed )
fi

"$python_bin" "${pytest_args[@]}"
'''
                }
            }
        }

        stage('Resolve input report') {
            steps {
                script {
                    if (params.VALIDATION_ONLY) {
                        if (!(params.INPUT_REPORT?.trim())) {
                            error('INPUT_REPORT is required when VALIDATION_ONLY is enabled')
                        }
                        env.FIRST_REPORT_PATH = params.INPUT_REPORT.trim()
                        echo "Validation-only mode, input report: ${env.FIRST_REPORT_PATH}"
                        return
                    }

                    def latestReport = sh(
                        script: '''#!/usr/bin/env bash
set -euo pipefail

python_bin="python3"
if [ -f "$PYTHON_BIN_FILE" ]; then
  python_bin="$(tr -d '\r\n' < "$PYTHON_BIN_FILE")"
fi
if [ ! -x "$python_bin" ]; then
  python_bin=".venv/bin/python"
fi

latest_report="$("$python_bin" -c "from pathlib import Path; import sys; reports = sorted(Path('reports').glob('partner_links_mobile_*.xlsx'), key=lambda p: p.stat().st_mtime, reverse=True); sys.exit(1) if not reports else print(reports[0])")"
printf '%s' "$latest_report"
''',
                        returnStdout: true
                    ).trim()
                    if (!(latestReport?.trim())) {
                        error('First iteration report not found after stage 1')
                    }
                    env.FIRST_REPORT_PATH = latestReport
                    echo "First iteration report: ${env.FIRST_REPORT_PATH}"
                }
            }
        }

        stage('Validate partner links') {
            steps {
                script {
                    if (!(env.FIRST_REPORT_PATH?.trim())) {
                        error('First iteration report path is missing')
                    }

                    withCredentials([
                        string(credentialsId: 'telegram_proxy_url', variable: 'TELEGRAM_PROXY_URL'),
                        string(credentialsId: 'telegram_proxy_auth_secret', variable: 'TELEGRAM_PROXY_AUTH_SECRET'),
                        string(credentialsId: 'telegram_proxy_global_test', variable: 'TELEGRAM_PROXY_CHAT_CREDENTIAL')
                    ]) {
                        sh '''#!/usr/bin/env bash
set -euo pipefail

python_bin="python3"
if [ -f "$PYTHON_BIN_FILE" ]; then
  python_bin="$(tr -d '\r\n' < "$PYTHON_BIN_FILE")"
fi
if [ ! -x "$python_bin" ]; then
  python_bin=".venv/bin/python"
fi

if [ "${USE_FINAL_URL_AS_FALLBACK}" = "true" ]; then
  "$python_bin" -m src.validate_partner_links \
    --input-report "$FIRST_REPORT_PATH" \
    --reference-file "$REFERENCE_LINKS_FILE" \
    --output-report "$VALIDATION_REPORT_PATH" \
    --run-mode "$RUN_MODE" \
    --use-final-url-as-fallback
else
  "$python_bin" -m src.validate_partner_links \
    --input-report "$FIRST_REPORT_PATH" \
    --reference-file "$REFERENCE_LINKS_FILE" \
    --output-report "$VALIDATION_REPORT_PATH" \
    --run-mode "$RUN_MODE"
fi
'''
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/*.xlsx,artifacts/**/*', allowEmptyArchive: true
            sh '''#!/usr/bin/env bash
set +e
rm -rf artifacts .pytest_cache pytest-cache-files-* __pycache__
exit 0
'''
            script {
                if (params.ENABLE_PERIODIC_ARTIFACT_PURGE) {
                    sh '''#!/usr/bin/env bash
set +e

purge_every="${PERIODIC_PURGE_EVERY:-5}"
if ! [[ "$purge_every" =~ ^[0-9]+$ ]] || [ "$purge_every" -lt 2 ]; then
  purge_every=5
fi

if ! [[ "$BUILD_NUMBER" =~ ^[0-9]+$ ]]; then
  echo "[PURGE] BUILD_NUMBER is not numeric, skip."
  exit 0
fi

build_number="$BUILD_NUMBER"
if (( build_number % purge_every != 0 )); then
  echo "[PURGE] Skip: build #$build_number is not each $purge_every-th run."
  exit 0
fi

if [ -z "${JENKINS_HOME:-}" ] || [ -z "${JOB_NAME:-}" ]; then
  echo "[PURGE] JENKINS_HOME or JOB_NAME is empty, skip."
  exit 0
fi

job_path="$(printf '%s' "$JOB_NAME" | sed 's#/#/jobs/#g')"
builds_dir="$JENKINS_HOME/jobs/$job_path/builds"
if [ ! -d "$builds_dir" ]; then
  echo "[PURGE] Builds dir not found: $builds_dir"
  exit 0
fi

echo "[PURGE] Running periodic purge for $JOB_NAME at build #$build_number (every $purge_every)"
find "$builds_dir" -mindepth 1 -maxdepth 1 -type d ! -name "$BUILD_NUMBER" -print0 | while IFS= read -r -d '' build_dir; do
  rm -rf "$build_dir/archive" "$build_dir/allure-report"
done
echo "[PURGE] Done."
'''
                } else {
                    echo 'Periodic artifact purge disabled by parameter.'
                }
            }
        }
    }
}
