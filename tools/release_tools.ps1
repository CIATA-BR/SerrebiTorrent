param(
    [Parameter(Mandatory = $true)]
    [string]$NotesPath,
    [string]$Range
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$versionFile = Join-Path $repoRoot "app_version.py"
if (-not (Test-Path $versionFile)) {
    throw "Version file not found: $versionFile"
}
$versionLine = Select-String -Path $versionFile -Pattern "^APP_VERSION\s*=" | Select-Object -First 1
if (-not $versionLine) {
    throw "APP_VERSION not found in $versionFile"
}
if ($versionLine.Line -match 'APP_VERSION\s*=\s*"(?<ver>\d+\.\d+\.\d+)"') {
    $minVersion = [version]$Matches.ver
} else {
    throw "APP_VERSION format invalid in $versionFile"
}

$tags = git tag --list "v*.*.*" | Where-Object { $_ -match "^v\d+\.\d+\.\d+$" }
$validTags = $tags | Where-Object { [version]($_.TrimStart("v")) -ge $minVersion }
$latest = $null
if ($validTags) {
    $latest = $validTags | Sort-Object { [version]($_.TrimStart("v")) } | Select-Object -Last 1
}

$base = if ($latest) { [version]$latest.TrimStart("v") } else { $minVersion }
if (-not $Range) {
    $Range = if ($latest) { "$latest..HEAD" } else { "HEAD" }
}
$range = $Range

# -split applies per element, so the log has to be joined back into one string
# first; otherwise every line becomes its own "commit" and each line of a commit
# body is emitted as a separate release-notes bullet. The split leaves the
# newline that followed the separator on the next chunk, hence the Trim.
$log = (git log $range --pretty=format:%s`n%b`n--END--) -join "`n"
$commits = $log -split "(?m)^--END--\s*$" |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -ne "" }

$breaking = $false
$feature = $false

foreach ($msg in $commits) {
    if ($msg -match "BREAKING CHANGE" -or $msg -match "!:") {
        $breaking = $true
    }
    if ($msg -match "(^|\s)feat" -or $msg -match "feature") {
        $feature = $true
    }
}

if (-not $latest) {
    $next = $minVersion
} elseif ($breaking) {
    $next = [version]::new($base.Major + 1, 0, 0)
} elseif ($feature) {
    $next = [version]::new($base.Major, $base.Minor + 1, 0)
} else {
    $next = [version]::new($base.Major, $base.Minor, $base.Build + 1)
}
if ($next -lt $minVersion) {
    $next = $minVersion
}

$breakingItems = @()
$featureItems = @()
$fixItems = @()
$otherItems = @()

foreach ($msg in $commits) {
    $subject = ($msg -split "`n")[0].Trim()
    if (-not $subject) {
        continue
    }
    # A merge subject names the branch, not the change; the commits it brought in
    # are already in the range.
    if ($subject -match "^Merge (pull request|branch) ") {
        continue
    }
    if ($msg -match "BREAKING CHANGE" -or $msg -match "!:") {
        $breakingItems += $subject
        continue
    }
    if ($subject -match "^(feat|feature)(\(|:|\s)" -or $subject -match "feature") {
        $featureItems += $subject
        continue
    }
    if ($subject -match "^(fix)(\(|:|\s)" -or $subject -match "fix") {
        $fixItems += $subject
        continue
    }
    $otherItems += $subject
}

# A branch that syncs one file per commit repeats the same subject many times;
# list each distinct subject once, in first-seen order.
$breakingItems = @($breakingItems | Select-Object -Unique)
$featureItems = @($featureItems | Select-Object -Unique)
$fixItems = @($fixItems | Select-Object -Unique)
$otherItems = @($otherItems | Select-Object -Unique)

$lines = @()
$lines += "Breaking"
if ($breakingItems.Count -eq 0) { $lines += "- None" } else { $lines += $breakingItems | ForEach-Object { "- $_" } }
$lines += ""
$lines += "Features"
if ($featureItems.Count -eq 0) { $lines += "- None" } else { $lines += $featureItems | ForEach-Object { "- $_" } }
$lines += ""
$lines += "Fixes"
if ($fixItems.Count -eq 0) { $lines += "- None" } else { $lines += $fixItems | ForEach-Object { "- $_" } }
$lines += ""
$lines += "Other"
if ($otherItems.Count -eq 0) { $lines += "- None" } else { $lines += $otherItems | ForEach-Object { "- $_" } }
$lines += ""

Set-Content -Path $NotesPath -Value ($lines -join "`n") -Encoding UTF8

Write-Output "NEXT_VERSION=$($next.ToString())"
Write-Output "LATEST_TAG=$latest"
Write-Output "RELEASE_NOTES=$NotesPath"
