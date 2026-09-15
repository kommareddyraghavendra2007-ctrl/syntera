#!/usr/bin/env pwsh
# SYNTERA — one-shot GitHub push script
# Usage: .\deploy.ps1  (optionally: .\deploy.ps1 -Visibility private)

param(
    [string]$RepoName    = "syntera",
    [string]$Visibility  = "public",
    [string]$Description = "SYNTERA — Codebase Intelligence Platform"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  SYNTERA  →  GitHub Deploy Script    " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check prerequisites ────────────────────────────────────────────────
foreach ($tool in @("git", "gh")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$tool' not found." -ForegroundColor Red
        if ($tool -eq "git") { Write-Host "  Install: https://git-scm.com/download/win" }
        if ($tool -eq "gh")  { Write-Host "  Install: https://cli.github.com/" }
        exit 1
    }
}
Write-Host "[OK] git and gh are available" -ForegroundColor Green

# ── 2. Initialize git repo if needed ─────────────────────────────────────
if (-not (Test-Path ".git")) {
    Write-Host "[GIT] Initializing repository..." -ForegroundColor Yellow
    git init
    git branch -M main
} else {
    Write-Host "[GIT] Git repo already initialized" -ForegroundColor Green
}

# ── 3. Stage and commit ───────────────────────────────────────────────────
Write-Host "[GIT] Staging files..." -ForegroundColor Yellow
git add .

$status = git status --porcelain
if ($status) {
    Write-Host "[GIT] Creating initial commit..." -ForegroundColor Yellow
    git commit -m "Initial commit: SYNTERA Codebase Intelligence Platform"
} else {
    Write-Host "[GIT] Nothing to commit — working tree clean" -ForegroundColor Green
}

# ── 4. Authenticate with GitHub ───────────────────────────────────────────
Write-Host ""
Write-Host "[GH] Checking GitHub authentication..." -ForegroundColor Yellow
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[GH] Not logged in — starting browser auth..." -ForegroundColor Yellow
    gh auth login --web --git-protocol https
} else {
    Write-Host "[GH] Already authenticated" -ForegroundColor Green
}

# ── 5. Create repo and push ───────────────────────────────────────────────
Write-Host ""
Write-Host "[GH] Creating GitHub repository '$RepoName' ($Visibility)..." -ForegroundColor Yellow

$repoExists = gh repo view $RepoName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[GH] Repo already exists — adding remote and pushing..." -ForegroundColor Yellow
    $username = gh api user --jq .login
    git remote remove origin 2>$null
    git remote add origin "https://github.com/$username/$RepoName.git"
    git push -u origin main
} else {
    gh repo create $RepoName `
        "--$Visibility" `
        --description $Description `
        --source . `
        --remote origin `
        --push
}

# ── 6. Print result ───────────────────────────────────────────────────────
$username = gh api user --jq .login
$repoUrl  = "https://github.com/$username/$RepoName"

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  SUCCESS!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "  GitHub repo  : $repoUrl" -ForegroundColor White
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Render  (backend) → https://render.com   → New Blueprint → connect $repoUrl"
Write-Host "    2. Vercel  (frontend)→ https://vercel.com   → Add Project   → import $repoUrl"
Write-Host "       Root dir: frontend | Build: npm install --legacy-peer-deps && npm run build"
Write-Host ""
Write-Host "  See DEPLOY.md for the full step-by-step guide."
Write-Host ""
