param(
    [string]$HostName = "root@serrebiradio.com",
    [string]$Ref = "HEAD",
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$archive = Join-Path ([IO.Path]::GetTempPath()) (
    "SerrebiTorrent-source-{0}.zip" -f [guid]::NewGuid().ToString("N")
)
$remoteRoot = $null

function Invoke-Native {
    param([scriptblock]$Command, [string]$Description)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

Push-Location $root
try {
    Invoke-Native { git rev-parse --verify "$Ref^{commit}" | Out-Null } "Git ref validation"
    Invoke-Native { git archive --format=zip --output="$archive" $Ref } "Source archive creation"

    $remoteRoot = (& ssh -o BatchMode=yes $HostName "mktemp -d /root/SerrebiTorrent-app-build.XXXXXX").Trim()
    if ($LASTEXITCODE -ne 0 -or $remoteRoot -notmatch '^/root/SerrebiTorrent-app-build\.[A-Za-z0-9]+$') {
        throw "The remote host did not return a safe build directory: $remoteRoot"
    }

    Invoke-Native { scp -q "$archive" "${HostName}:${remoteRoot}/source.zip" } "Source upload"

    # Keep this a single line with no embedded double quotes or newlines. A
    # multi-line string loses its quoting on the way through ssh, which turns
    # "set -Eeuo pipefail" into a bare "set" that dumps the remote environment
    # and silently drops the error handling. A login shell is not used, so the
    # remote profile cannot print secrets into the build log.
    $remoteCommand = (
        "set -Eeuo pipefail; " +
        "mkdir -p '$remoteRoot/source'; " +
        "unzip -q '$remoteRoot/source.zip' -d '$remoteRoot/source'; " +
        "SERREBITORRENT_BUILD_VERSION='$Version' " +
        "bash '$remoteRoot/source/tools/build_linux.sh'"
    )
    Invoke-Native { ssh -o BatchMode=yes $HostName $remoteCommand } "Remote Linux build"

    $output = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
    New-Item -ItemType Directory -Force -Path $output | Out-Null
    $artifact = "SerrebiTorrent-v$Version-linux-x86_64.tar.gz"
    Invoke-Native {
        scp -q "${HostName}:${remoteRoot}/source/dist/$artifact" (Join-Path $output $artifact)
    } "Linux artifact download"
    Write-Host "Linux package: $(Join-Path $output $artifact)"
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    if ($remoteRoot -and $remoteRoot -match '^/root/SerrebiTorrent-app-build\.[A-Za-z0-9]+$') {
        & ssh -o BatchMode=yes $HostName "rm -rf -- '$remoteRoot'" | Out-Null
    }
}
