param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDir,

    [switch]$StripAffixNotes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$targetPath = (Resolve-Path -LiteralPath $TargetDir).ProviderPath

if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
    throw "Target directory not found: $TargetDir"
}

Write-Host "[INFO] Target path: $targetPath"

if (-not $StripAffixNotes) {
    Write-Host "[INFO] Build source copied without text changes."
    exit 0
}

$entryPattern = [regex]'(?m)^(tag(?:GDX\d+)?(?:Prefix|Suffix)[^=\r\n]*=)(.*)$'
$valuePattern = [regex]'^(?<label>.*)\((?<summary>[^()\r\n]*)\)(?<tail>\s*\u00B7?\s*)$'
$changedFiles = 0
$changedLines = 0

$targetFiles = Get-ChildItem -LiteralPath $targetPath -Recurse -File -Filter 'tags*items.txt'
foreach ($file in $targetFiles) {
    $content = [System.IO.File]::ReadAllText($file.FullName)

    $updated = $entryPattern.Replace($content, {
        param($match)

        $value = $match.Groups[2].Value
        $valueMatch = $valuePattern.Match($value)
        if (-not $valueMatch.Success) {
            return $match.Value
        }

        $script:changedLines++
        return $match.Groups[1].Value + $valueMatch.Groups['label'].Value + $valueMatch.Groups['tail'].Value
    })

    if ($updated -cne $content) {
        [System.IO.File]::WriteAllText($file.FullName, $updated, $utf8NoBom)
        $changedFiles++
    }
}

Write-Host "[INFO] Build source prepared: $changedFiles file(s), $changedLines line(s) stripped."
