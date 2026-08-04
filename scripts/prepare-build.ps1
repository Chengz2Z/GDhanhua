param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDir,

    [Parameter(Mandatory = $true)]
    [ValidateSet('with_desc', 'no_desc')]
    [string]$FilterProfile,

    [string]$FilterConfigPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$targetPath = (Resolve-Path -LiteralPath $TargetDir).ProviderPath
if ([string]::IsNullOrWhiteSpace($FilterConfigPath)) {
    $FilterConfigPath = Join-Path $PSScriptRoot 'text-filters.json'
}
$filterConfigFullPath = (Resolve-Path -LiteralPath $FilterConfigPath).ProviderPath

if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
    throw "Target directory not found: $TargetDir"
}

Write-Host "[INFO] Target path: $targetPath"
Write-Host "[INFO] Filter config: $filterConfigFullPath ($FilterProfile)"

$filterConfig = Get-Content -LiteralPath $filterConfigFullPath -Raw -Encoding UTF8 | ConvertFrom-Json
$profileProperty = $filterConfig.profiles.PSObject.Properties[$FilterProfile]
if ($null -eq $profileProperty) {
    throw "Filter profile not found: $FilterProfile"
}
$filterProfileConfig = $profileProperty.Value
$rulesProperty = $filterProfileConfig.PSObject.Properties['rules']
if ($null -eq $rulesProperty) {
    throw "$FilterProfile.rules must be an array."
}

$compiledRules = @()
$ruleConfigs = @($rulesProperty.Value)
for ($ruleIndex = 0; $ruleIndex -lt $ruleConfigs.Count; $ruleIndex++) {
    $ruleConfig = $ruleConfigs[$ruleIndex]
    $ruleLabel = "$FilterProfile.rules[$ruleIndex]"
    $includeProperty = $ruleConfig.PSObject.Properties['include']
    if ($null -eq $includeProperty) {
        throw "$ruleLabel.include must be an array."
    }
    $includePatterns = @($includeProperty.Value)
    $removeProperty = $ruleConfig.PSObject.Properties['remove_patterns']
    $replaceProperty = $ruleConfig.PSObject.Properties['replace_patterns']
    $removePatternStrings = @()
    if ($null -ne $removeProperty) {
        $removePatternStrings = @($removeProperty.Value)
    }
    $replaceConfigs = @()
    if ($null -ne $replaceProperty) {
        $replaceConfigs = @($replaceProperty.Value)
    }
    if (($removePatternStrings.Count -gt 0 -or $replaceConfigs.Count -gt 0) -and $includePatterns.Count -eq 0) {
        throw "$ruleLabel.include cannot be empty when filter operations are configured."
    }

    $removePatterns = @()
    foreach ($patternString in $removePatternStrings) {
        if (-not ($patternString -is [string]) -or $patternString.Length -eq 0) {
            throw "$ruleLabel.remove_patterns must contain non-empty strings."
        }
        try {
            $removePatterns += New-Object System.Text.RegularExpressions.Regex($patternString)
        }
        catch {
            throw "Invalid regex in $ruleLabel.remove_patterns: $patternString"
        }
    }

    $replacePatterns = @()
    for ($replaceIndex = 0; $replaceIndex -lt $replaceConfigs.Count; $replaceIndex++) {
        $replaceConfig = $replaceConfigs[$replaceIndex]
        $replaceLabel = "$ruleLabel.replace_patterns[$replaceIndex]"
        $replacePatternString = $replaceConfig.pattern
        $keepGroups = @($replaceConfig.keep_groups)
        if (-not ($replacePatternString -is [string]) -or $replacePatternString.Length -eq 0) {
            throw "$replaceLabel.pattern must be a non-empty string."
        }
        try {
            $replacePattern = New-Object System.Text.RegularExpressions.Regex($replacePatternString)
        }
        catch {
            throw "Invalid regex in $replaceLabel.pattern: $replacePatternString"
        }
        $validGroupNumbers = @($replacePattern.GetGroupNumbers())
        foreach ($group in $keepGroups) {
            if (-not ($group -is [int]) -and -not ($group -is [long])) {
                throw "$replaceLabel.keep_groups must contain positive integers."
            }
            if ($group -lt 1 -or -not ($validGroupNumbers -contains $group)) {
                throw "$replaceLabel.keep_groups contains out-of-range group: $group"
            }
        }
        $replacePatterns += [PSCustomObject]@{
            Pattern = $replacePattern
            KeepGroups = @($keepGroups)
        }
    }

    $compiledRules += [PSCustomObject]@{
        IncludePatterns = @($includePatterns)
        RemovePatterns = @($removePatterns)
        ReplacePatterns = @($replacePatterns)
    }
}

$configuredPatternCount = 0
foreach ($compiledRule in $compiledRules) {
    $configuredPatternCount += @($compiledRule.RemovePatterns).Count
    $configuredPatternCount += @($compiledRule.ReplacePatterns).Count
}

if ($configuredPatternCount -gt 0) {
    $filterChangedFiles = 0
    $filterChangedFields = 0
    $filterFiles = Get-ChildItem -LiteralPath $targetPath -Recurse -File
    foreach ($file in $filterFiles) {
        $relativePath = $file.FullName.Substring($targetPath.Length).TrimStart('\', '/').Replace('\', '/')
        $matchingRules = @()
        foreach ($compiledRule in $compiledRules) {
            if (
                @($compiledRule.RemovePatterns).Count -eq 0 -and
                @($compiledRule.ReplacePatterns).Count -eq 0
            ) {
                continue
            }
            $included = $false
            foreach ($includePattern in @($compiledRule.IncludePatterns)) {
                if ($file.Name -like $includePattern -or $relativePath -like $includePattern) {
                    $included = $true
                    break
                }
            }
            if (-not $included) {
                continue
            }
            $matchingRules += $compiledRule
        }
        if ($matchingRules.Count -eq 0) {
            continue
        }

        $content = [System.IO.File]::ReadAllText($file.FullName)
        $updated = $content
        $replacements = 0
        foreach ($compiledRule in $matchingRules) {
            foreach ($replaceConfig in @($compiledRule.ReplacePatterns)) {
                $matches = $replaceConfig.Pattern.Matches($updated)
                $replacements += $matches.Count
                $keepGroups = @($replaceConfig.KeepGroups)
                $updated = $replaceConfig.Pattern.Replace($updated, {
                    param($match)

                    $parts = foreach ($group in $keepGroups) {
                        $match.Groups[$group].Value
                    }
                    return $parts -join ''
                })
            }
            foreach ($removePattern in @($compiledRule.RemovePatterns)) {
                $matches = $removePattern.Matches($updated)
                $replacements += $matches.Count
                $updated = $removePattern.Replace($updated, '')
            }
        }

        if ($updated -cne $content) {
            [System.IO.File]::WriteAllText($file.FullName, $updated, $utf8NoBom)
            $filterChangedFiles++
            $filterChangedFields += $replacements
        }
    }

    Write-Host "[INFO] Text filters applied ($FilterProfile): $filterChangedFiles file(s), $filterChangedFields field(s)."
}
else {
    Write-Host "[INFO] Text filters applied ($FilterProfile): no configured rule patterns."
}
