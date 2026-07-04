$ErrorActionPreference = "Stop"

$projectDir = $PSScriptRoot
Set-Location -LiteralPath $projectDir

$pythonExe = "C:\Users\28471\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$githubDesktopGit = Get-ChildItem -Path "$env:LOCALAPPDATA\GitHubDesktop" -Recurse -Filter "git.exe" -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -like "*\resources\app\git\cmd\git.exe" } |
  Sort-Object FullName -Descending |
  Select-Object -First 1
$bundledGitRoot = "C:\Users\28471\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git"
$bundledGitExe = "$bundledGitRoot\cmd\git.exe"

if ($githubDesktopGit) {
  $gitExe = $githubDesktopGit.FullName
  $gitRoot = Split-Path -Parent (Split-Path -Parent $gitExe)
  $env:PATH = "$gitRoot\mingw64\bin;$gitRoot\mingw64\libexec\git-core;$gitRoot\cmd;$env:PATH"
  $env:GIT_EXEC_PATH = "$gitRoot\mingw64\libexec\git-core"
} else {
  $gitExe = $bundledGitExe
  $env:PATH = "$bundledGitRoot\mingw64\bin;$bundledGitRoot\mingw64\libexec\git-core;$bundledGitRoot\cmd;$env:PATH"
  $env:GIT_EXEC_PATH = "$bundledGitRoot\mingw64\libexec\git-core"
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
  Write-Host "Python not found: $pythonExe" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

if (-not (Test-Path -LiteralPath $gitExe)) {
  Write-Host "Git not found: $gitExe" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

function Invoke-NativeAllowFail {
  param(
    [string]$Exe,
    [string[]]$Arguments
  )
  $oldPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & $Exe @Arguments 1>$null 2>$null
  $code = $LASTEXITCODE
  $ErrorActionPreference = $oldPreference
  return $code
}

Write-Host "[1/4] Generate GitHub Pages static album: docs..."
& $pythonExe "export_static.py"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Export failed" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

$repoCheck = Invoke-NativeAllowFail $gitExe @("rev-parse", "--is-inside-work-tree")
if ($repoCheck -eq 0) {
  Write-Host "[2/4] Git repository already exists"
} else {
  if (Test-Path -LiteralPath ".git") {
    $backupName = ".git-broken-" + (Get-Date -Format "yyyyMMddHHmmss")
    Write-Host "[2/4] Broken .git found. Backup to $backupName"
    Rename-Item -LiteralPath ".git" -NewName $backupName
  }
  Write-Host "[2/4] Initialize Git repository..."
  & $gitExe init
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Git init failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
  }
}

$nameCheck = Invoke-NativeAllowFail $gitExe @("config", "user.name")
if ($nameCheck -ne 0) {
  & $gitExe config user.name "Youzi Photo"
}

$emailCheck = Invoke-NativeAllowFail $gitExe @("config", "user.email")
if ($emailCheck -ne 0) {
  & $gitExe config user.email "youzi@example.com"
}

$originCheck = Invoke-NativeAllowFail $gitExe @("remote", "get-url", "origin")
if ($originCheck -ne 0) {
  Write-Host ""
  Write-Host "Paste your GitHub repository URL, for example:"
  Write-Host "https://github.com/your-name/youzi-album.git"
  $repoUrl = Read-Host "GitHub repo URL"
  & $gitExe remote add origin $repoUrl
}

Write-Host "[3/4] Commit changes..."
& $gitExe add .
& $gitExe commit -m "Update customer album"
if ($LASTEXITCODE -ne 0) {
  Write-Host "No new commit created. Continue to push..."
}

Write-Host "[4/4] Push to GitHub..."
& $gitExe branch -M main
& $gitExe push -u origin main
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Push failed. Please check the GitHub login window or repository URL." -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

Write-Host ""
Write-Host "Done. GitHub Pages will deploy automatically. Visit later:"
Write-Host "https://www.youzizhijia.dpdns.org"
Read-Host "Press Enter to exit"
