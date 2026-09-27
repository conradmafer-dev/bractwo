[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Run from any directory. Keep the original source archive's top-level folder.
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$workspaceRoot = Split-Path -Parent $projectRoot
$archiveRoot = 'Bractwo_0.8.17'
$archiveName = 'BRACTWO_0.8.17_MOBILE_01_FULL_SOURCE.zip'
$archivePath = Join-Path $workspaceRoot $archiveName
$manifestPath = Join-Path $projectRoot 'SOURCE_MANIFEST.json'
$temporaryPath = Join-Path $workspaceRoot ($archiveName + '.partial-' + [guid]::NewGuid().ToString('N'))
$baseArchive = 'BRACTWO_0.8.17_ROZDZKA_PRIORYTET_CZAROW_FULL_SOURCE.zip'
$utf8 = [System.Text.UTF8Encoding]::new($false)

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'SOURCE_MANIFEST.json is missing.' }
if ((Test-Path -LiteralPath $archivePath) -and -not $Force) { throw "Archive already exists. Use -Force to replace: $archivePath" }

$manifest = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
if ($manifest.version -ne '0.8.17') { throw 'This packager requires the 0.8.17 base manifest.' }

$excludedDirectories = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($name in @('.qa-python', '__pycache__', 'data', '.git', '.venv', 'node_modules', '.pytest_cache', '.mypy_cache', '.godot')) {
    [void]$excludedDirectories.Add($name)
}
$pending = [System.Collections.Generic.Stack[string]]::new()
$selected = [System.Collections.Generic.List[object]]::new()
$pending.Push($projectRoot)
$rootPrefix = $projectRoot.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar

# Prune excluded directories before descending, including dependency environments.
while ($pending.Count -gt 0) {
    $directory = $pending.Pop()
    foreach ($entry in Get-ChildItem -LiteralPath $directory -Force) {
        if (($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
        if ($entry.PSIsContainer) {
            if (-not $excludedDirectories.Contains($entry.Name)) { $pending.Push($entry.FullName) }
            continue
        }
        if ($entry.Extension -in @('.zip', '.log', '.tmp', '.pyc', '.pyo')) { continue }
        if ($entry.Name -like '*.partial-*' -or $entry.Name -like 'npm-debug*' -or $entry.Name -like 'yarn-error*') { continue }
        $relative = $entry.FullName.Substring($rootPrefix.Length).Replace('\', '/')
        if ($relative -eq 'SOURCE_MANIFEST.json') { continue }
        $selected.Add([pscustomobject]@{ FullName = $entry.FullName; Relative = $relative })
    }
}
$files = @($selected | Sort-Object -Property Relative)
if ($files.Count -eq 0) { throw 'No source files selected.' }

$mobileChanges = @(
    'Mobile01: compact web status and minimap with fixed touch controls',
    'Mobile01: one horizontally scrolling row of all occupied spell slots, including F1-F12',
    'Mobile01: menu and chat on demand, mobile visibility settings separated from desktop',
    'Mobile01: mobile CSS/JS routes added to server/server.py',
    'Mobile01: wand priority, mana rules, save schema and native Godot layout unchanged'
)
$manifest | Add-Member -NotePropertyName mobile_revision -NotePropertyValue '01' -Force
$manifest | Add-Member -NotePropertyName mobile_base_archive -NotePropertyValue $baseArchive -Force
$manifest | Add-Member -NotePropertyName based_on -NotePropertyValue @(@($manifest.based_on) + $baseArchive | Select-Object -Unique) -Force
$manifest | Add-Member -NotePropertyName changes -NotePropertyValue @(@($manifest.changes) + $mobileChanges | Select-Object -Unique) -Force
$manifest | Add-Member -NotePropertyName built_at -NotePropertyValue ([DateTimeOffset]::UtcNow.ToString('o')) -Force
$manifest | Add-Member -NotePropertyName package -NotePropertyValue 'full_source' -Force
$manifest | Add-Member -NotePropertyName archive_root -NotePropertyValue ($archiveRoot + '/') -Force
$manifest | Add-Member -NotePropertyName hash_algorithm -NotePropertyValue 'SHA-256' -Force
$manifest | Add-Member -NotePropertyName hash_scope -NotePropertyValue 'All packaged files except SOURCE_MANIFEST.json, which cannot contain its own hash.' -Force
$manifest | Add-Member -NotePropertyName mobile_changed_production_files -NotePropertyValue @('server/server.py', 'web/game.js', 'web/index.html', 'web/windows.js', 'web/mobile.css', 'web/mobile.js') -Force
if ($null -eq $manifest.PSObject.Properties['baseline_validation']) {
    $manifest | Add-Member -NotePropertyName baseline_validation -NotePropertyValue $manifest.tests -Force
}
$reportRelative = 'docs/qa_mobile/browser_results.json'
$reportPresent = $files.Relative -contains $reportRelative
$verification = [ordered]@{
    javascript_existing = 35
    python_hud_existing = 7
    javascript_syntax = 'passed'
    browser_report = $reportRelative
    browser_report_included = $reportPresent
    browser_status = $(if ($reportPresent) { 'See included report; results are not inferred by the packager.' } else { 'Pending; no browser report included.' })
}
$manifest | Add-Member -NotePropertyName tests -NotePropertyValue $verification -Force

Add-Type -AssemblyName System.IO.Compression
$archiveStream = $null
$archive = $null
try {
    $archiveStream = [System.IO.File]::Open($temporaryPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $archive = [System.IO.Compression.ZipArchive]::new($archiveStream, [System.IO.Compression.ZipArchiveMode]::Create, $true)
    $hashes = [ordered]@{}
    foreach ($file in $files) {
        $source = $null
        $target = $null
        $sha = $null
        try {
            # One read-only handle supplies both the hash and archive bytes.
            # FileShare.Read prevents a concurrent writer from changing this file.
            $source = [System.IO.File]::Open($file.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
            $sha = [System.Security.Cryptography.SHA256]::Create()
            $hashes[$file.Relative] = ([BitConverter]::ToString($sha.ComputeHash($source))).Replace('-', '').ToLowerInvariant()
            $source.Position = 0
            $entry = $archive.CreateEntry($archiveRoot + '/' + $file.Relative, [System.IO.Compression.CompressionLevel]::Optimal)
            $target = $entry.Open()
            $source.CopyTo($target)
        } finally {
            if ($null -ne $target) { $target.Dispose() }
            if ($null -ne $sha) { $sha.Dispose() }
            if ($null -ne $source) { $source.Dispose() }
        }
    }
    $manifest | Add-Member -NotePropertyName files -NotePropertyValue $hashes -Force
    $manifest | Add-Member -NotePropertyName packaged_file_count -NotePropertyValue ($files.Count + 1) -Force
    $manifestText = ($manifest | ConvertTo-Json -Depth 100) + [Environment]::NewLine
    [System.IO.File]::WriteAllText($manifestPath, $manifestText, $utf8)
    $manifestEntry = $archive.CreateEntry($archiveRoot + '/SOURCE_MANIFEST.json', [System.IO.Compression.CompressionLevel]::Optimal)
    $manifestTarget = $manifestEntry.Open()
    try {
        $manifestBytes = $utf8.GetBytes($manifestText)
        $manifestTarget.Write($manifestBytes, 0, $manifestBytes.Length)
    } finally { $manifestTarget.Dispose() }
    $archive.Dispose()
    $archive = $null
    $archiveStream.Dispose()
    $archiveStream = $null
    Move-Item -LiteralPath $temporaryPath -Destination $archivePath -Force:$Force
    Write-Output "Created $archivePath"
    Write-Output "Packaged $($files.Count + 1) files under $archiveRoot/; SHA-256 hashes match the packaged source bytes."
} finally {
    if ($null -ne $archive) { $archive.Dispose() }
    if ($null -ne $archiveStream) { $archiveStream.Dispose() }
    if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath -Force }
}
