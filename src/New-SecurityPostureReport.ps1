#Requires -Modules Az.Accounts, Az.ResourceGraph, Az.OperationalInsights
<#
.SYNOPSIS
    Generates a standalone monthly Security Posture HTML report from Defender for
    Cloud (Secure Score + assessments via Azure Resource Graph) and Microsoft
    Sentinel (incidents via Log Analytics). Output is a single self-contained
    .html file (no external/CDN calls) suitable for firewalled corporate use.

.DESCRIPTION
    One script, three data sources, one HTML out:
      1. Azure Resource Graph  -> Secure Score per subscription + unhealthy assessments
      2. Defender REST API     -> Secure Score percentage (optional cross-check)
      3. Log Analytics (KQL)   -> open Sentinel incidents
    The script injects a JSON blob into a template between the markers
    /*__REPORT_DATA_START__*/ ... /*__REPORT_DATA_END__*/.

.PARAMETER TemplatePath
    Path to the HTML template (the sample file ships as both sample and template).

.PARAMETER OutputFolder
    Folder where the dated report is written.

.PARAMETER WorkspaceId
    Log Analytics / Sentinel workspace *customer ID* (GUID) for the incident query.

.PARAMETER SubscriptionIds
    Optional explicit subscription scope. Omit to use every subscription you can read.

.EXAMPLE
    .\New-SecurityPostureReport.ps1 -WorkspaceId "<guid>" -Verbose

.NOTES
    Auth: run interactively (Connect-AzAccount) or unattended via a service
    principal / managed identity that has Security Reader + Log Analytics Reader.
#>

[CmdletBinding()]
param(
    [string]   $TemplatePath  = ".\SecurityPosture-Template.html",
    [string]   $OutputFolder  = ".\reports",
    [string]   $WorkspaceId   = "",                 # Sentinel workspace customer GUID
    [string[]] $SubscriptionIds = @(),              # empty = all readable subscriptions
    [string]   $OrgName       = "Cloud Operations",
    [int]      $IncidentLookbackDays = 35
)

$ErrorActionPreference = 'Stop'
$tz   = "South Africa Standard Time"
$now  = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([datetime]::UtcNow, $tz)
$period = $now.ToString("MMMM yyyy")

# Severity name -> numeric weight used by the report UI
$SevMap = @{ 'Critical'=4; 'High'=3; 'Medium'=2; 'Low'=1 }
function Get-SevName([string]$s){ if($SevMap.ContainsKey($s)){ $s } else { 'Low' } }

# ----------------------------------------------------------------------
# 0. Connect
# ----------------------------------------------------------------------
if (-not (Get-AzContext)) {
    Write-Verbose "No Az context found - connecting..."
    Connect-AzAccount | Out-Null
}

# Resolve subscription scope
if (-not $SubscriptionIds -or $SubscriptionIds.Count -eq 0) {
    $SubscriptionIds = (Get-AzSubscription | Where-Object State -eq 'Enabled').Id
}
Write-Verbose ("Scope: {0} subscription(s)" -f $SubscriptionIds.Count)

# Friendly names for the dropdown
$subNames = @{}
foreach ($s in (Get-AzSubscription)) { $subNames[$s.Id] = $s.Name }

# ----------------------------------------------------------------------
# 1. Resource Graph - Secure Score per subscription
#    KQL: securityresources / microsoft.security/securescores
# ----------------------------------------------------------------------
$kqlScore = @"
securityresources
| where type == 'microsoft.security/securescores'
| where name == 'ascScore'
| extend pct = round(todouble(properties.score.percentage) * 100, 0),
         cur = round(todouble(properties.score.current), 0),
         max = round(todouble(properties.score.max), 0)
| project subscriptionId, pct, cur, max
"@

# ----------------------------------------------------------------------
# 2. Resource Graph - Unhealthy assessments (the "resources with issues")
#    KQL: securityresources / microsoft.security/assessments
# ----------------------------------------------------------------------
$kqlAssess = @"
securityresources
| where type == 'microsoft.security/assessments'
| extend status   = tostring(properties.status.code)
| where status == 'Unhealthy'
| extend rec        = tostring(properties.displayName),
         sev        = tostring(properties.metadata.severity),
         category   = tostring(properties.metadata.categories[0]),
         resourceId = tolower(tostring(properties.resourceDetails.Id))
| extend afterProv  = split(resourceId, '/providers/')
| extend tail       = iff(array_length(afterProv) > 1, tostring(afterProv[-1]), resourceId)
| extend resourceType = iff(array_length(afterProv) > 1,
            strcat(tostring(split(tail,'/')[0]), '/', tostring(split(tail,'/')[1])), 'unknown'),
         resourceName = tostring(split(resourceId, '/')[-1])
| where isnotempty(resourceName)
| project subscriptionId, resourceName, resourceType, rec, sev, status, category
"@

# Run RG queries with paging (results can exceed 1000 rows)
function Invoke-Graph([string]$Query, [string[]]$Subs) {
    $all = @(); $skip = 0; $first = 1000
    do {
        $page = Search-AzGraph -Query $Query -Subscription $Subs -First $first -Skip $skip
        if ($page) { $all += $page; $skip += $page.Count }
    } while ($page -and $page.Count -eq $first)
    return $all
}

Write-Verbose "Querying Resource Graph: secure scores..."
$scoreRows  = Invoke-Graph -Query $kqlScore  -Subs $SubscriptionIds
Write-Verbose "Querying Resource Graph: unhealthy assessments..."
$assessRows = Invoke-Graph -Query $kqlAssess -Subs $SubscriptionIds

$scoreBySub = @{}
foreach ($r in $scoreRows) { $scoreBySub[$r.subscriptionId] = $r }

# ----------------------------------------------------------------------
# 3. (Optional cross-check) Secure Score via Defender REST API
#    GET .../Microsoft.Security/secureScores/ascScore?api-version=2020-01-01
#    Returns properties.score.percentage as a 0..1 fraction.
# ----------------------------------------------------------------------
function Get-SecureScoreApi([string]$SubId) {
    try {
        $token = (Get-AzAccessToken -ResourceUrl "https://management.azure.com/").Token
        $uri   = "https://management.azure.com/subscriptions/$SubId/providers/Microsoft.Security/secureScores/ascScore?api-version=2020-01-01"
        $resp  = Invoke-RestMethod -Uri $uri -Headers @{ Authorization = "Bearer $token" } -Method GET
        return [pscustomobject]@{
            pct = [math]::Round($resp.properties.score.percentage * 100, 0)
            cur = [math]::Round($resp.properties.score.current, 0)
            max = [math]::Round($resp.properties.score.max, 0)
        }
    } catch { Write-Verbose "REST score unavailable for $SubId: $($_.Exception.Message)"; return $null }
}

# ----------------------------------------------------------------------
# 4. Sentinel incidents via Log Analytics (KQL: SecurityIncident)
# ----------------------------------------------------------------------
$incidents = @()
if ($WorkspaceId) {
    $kqlInc = @"
SecurityIncident
| where TimeGenerated > ago(${IncidentLookbackDays}d)
| summarize arg_max(TimeGenerated, *) by IncidentNumber
| where Status != 'Closed'
| project IncidentNumber, Title, Severity, Status, CreatedTime
| order by CreatedTime desc
"@
    Write-Verbose "Querying Log Analytics: open incidents..."
    try {
        $r = Invoke-AzOperationalInsightsQuery -WorkspaceId $WorkspaceId -Query $kqlInc
        $incidents = $r.Results
    } catch { Write-Warning "Incident query failed: $($_.Exception.Message)" }
} else {
    Write-Warning "No -WorkspaceId supplied; skipping Sentinel incidents."
}

# Sentinel incidents are workspace-scoped, not cleanly per-subscription.
# Attach them to the subscription that hosts the workspace (first in scope by default).
$incidentSub = $SubscriptionIds[0]

# ----------------------------------------------------------------------
# 5. Shape the data object the HTML expects
# ----------------------------------------------------------------------
$assessBySub = $assessRows | Group-Object subscriptionId -AsHashTable -AsString

$subscriptions = foreach ($subId in $SubscriptionIds) {
    $sc = $scoreBySub[$subId]
    $issues = @()
    if ($assessBySub.ContainsKey($subId)) {
        $issues = foreach ($a in $assessBySub[$subId]) {
            $sn = Get-SevName $a.sev
            [pscustomobject]@{
                resource = $a.resourceName
                type     = $a.resourceType
                rec      = $a.rec
                control  = if ($a.category) { $a.category } else { 'General' }
                sevName  = $sn
                sev      = $SevMap[$sn]
                status   = $a.status
            }
        }
    }
    $incForSub = @()
    if ($subId -eq $incidentSub) {
        $incForSub = foreach ($i in $incidents) {
            [pscustomobject]@{
                number   = "INC-$($i.IncidentNumber)"
                title    = $i.Title
                severity = Get-SevName $i.Severity
                status   = $i.Status
                created  = ([datetime]$i.CreatedTime).ToString("yyyy-MM-dd")
            }
        }
    }
    [pscustomobject]@{
        id       = $subId
        name     = if ($subNames[$subId]) { $subNames[$subId] } else { $subId }
        scorePct = if ($sc) { [int]$sc.pct } else { 0 }
        current  = if ($sc) { [int]$sc.cur } else { 0 }
        max      = if ($sc) { [int]$sc.max } else { 0 }
        issues   = @($issues)
        incidents= @($incForSub)
    }
}

# Roll-up KPIs
$allIssues = $subscriptions.issues
$overall = [pscustomobject]@{
    scorePct      = if ($scoreRows) { [int]([math]::Round(($scoreRows.pct | Measure-Object -Average).Average,0)) } else { 0 }
    current       = ($subscriptions.current | Measure-Object -Sum).Sum
    max           = ($subscriptions.max     | Measure-Object -Sum).Sum
    critical      = @($allIssues | Where-Object sevName -eq 'Critical').Count
    high          = @($allIssues | Where-Object sevName -eq 'High').Count
    medium        = @($allIssues | Where-Object sevName -eq 'Medium').Count
    openIncidents = @($incidents).Count
}

$report = [pscustomobject]@{
    meta = [pscustomobject]@{
        org       = $OrgName
        period    = $period
        generated = $now.ToString("yyyy-MM-dd HH:mm") + " SAST"
        tenant    = (Get-AzContext).Tenant.Id
    }
    overall       = $overall
    baseline      = @(
        @{ control='MFA on all privileged accounts'; target='100%';            rationale='Entra ID / PIM eligible-only admin roles, MFA enforced.' },
        @{ control='Defender for Cloud plans';        target='All plans ON';     rationale='Servers, Storage, Containers, Key Vault, SQL.' },
        @{ control='Disk encryption';                 target='100% of VMs/disks';rationale='Encryption at rest baseline.' },
        @{ control='Public network exposure';         target='0 mgmt ports open';rationale='No 22/3389 from Any; use Bastion / JIT.' },
        @{ control='Secure Score';                    target='&ge; 80%';         rationale='Defender for Cloud overall target.' },
        @{ control='Critical CVEs';                   target='0 > 14 days';      rationale='Vulnerability assessment SLA.' },
        @{ control='Diagnostic logs to Log Analytics';target='100% of resources';rationale='Sentinel ingestion + audit evidence.' }
    )
    subscriptions = @($subscriptions)
}

$json = $report | ConvertTo-Json -Depth 8

# ----------------------------------------------------------------------
# 6. Inject into template and write output
# ----------------------------------------------------------------------
if (-not (Test-Path $TemplatePath)) { throw "Template not found: $TemplatePath" }
if (-not (Test-Path $OutputFolder)) { New-Item -ItemType Directory -Path $OutputFolder | Out-Null }

$tpl = Get-Content $TemplatePath -Raw
$pattern = '(?s)/\*__REPORT_DATA_START__\*/.*?/\*__REPORT_DATA_END__\*/'
$replacement = "/*__REPORT_DATA_START__*/ $json /*__REPORT_DATA_END__*/"
$out = [regex]::Replace($tpl, $pattern, { param($m) $replacement })

$outFile = Join-Path $OutputFolder ("SecurityPosture-{0}.html" -f $now.ToString("yyyy-MM"))
Set-Content -Path $outFile -Value $out -Encoding UTF8

Write-Host "Report written: $outFile" -ForegroundColor Green
Write-Host ("  Secure Score (avg): {0}%   Critical: {1}  High: {2}  Open incidents: {3}" -f `
    $overall.scorePct, $overall.critical, $overall.high, $overall.openIncidents)
