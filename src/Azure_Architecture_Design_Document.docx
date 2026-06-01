#requires -Version 7.0
<#
================================================================================
  New-SecurityPostureReport.ps1
  Monthly Azure security posture report generator (single-file).

  Collects, per subscription:
    * Defender for Cloud secure score          (Microsoft.Security REST API)
    * Secure-score controls losing points       (Azure Resource Graph)
    * Unhealthy resource assessments / findings  (Azure Resource Graph)
    * Open Microsoft Sentinel incidents          (Log Analytics, optional)
  ...then renders a standalone HTML report (no external dependencies) with a
  global subscription dropdown that re-scopes the whole report.

  Modules:  Az.Accounts, Az.ResourceGraph, Az.OperationalInsights (optional)
            Install-Module Az.Accounts, Az.ResourceGraph, Az.OperationalInsights -Scope CurrentUser

  Run locally (interactive):
      Connect-AzAccount
      ./New-SecurityPostureReport.ps1 -SentinelWorkspaceId <guid>

  Run unattended (Automation Account / runbook / pipeline):
      ./New-SecurityPostureReport.ps1 -UseManagedIdentity -SentinelWorkspaceId <guid>

  Required RBAC (read-only): "Security Reader" + "Reader" at the scope you
  report on, plus "Log Analytics Reader" on the Sentinel workspace.
================================================================================
#>

[CmdletBinding()]
param(
    [string]   $OutputPath          = "./security-posture-report-$(Get-Date -Format yyyy-MM).html",
    [string[]] $SubscriptionId,                       # omit = all subscriptions you can read
    [double]   $TargetScorePct       = 85,            # baseline target shown on the Baseline tab
    [string]   $SentinelWorkspaceId,                  # Log Analytics workspace GUID (optional)
    [switch]   $UseManagedIdentity,                   # for runbooks / pipelines
    [string]   $BlobContainerSas                      # optional: SAS URL to upload the report as evidence
)

$ErrorActionPreference = 'Stop'
$ApiVersion = '2020-01-01'

# ---------------------------------------------------------------------------
# 1. Connect
# ---------------------------------------------------------------------------
if (-not (Get-AzContext)) {
    if ($UseManagedIdentity) { Connect-AzAccount -Identity | Out-Null }
    else                     { Connect-AzAccount       | Out-Null }
}

# ---------------------------------------------------------------------------
# 2. KQL queries (Azure Resource Graph)
# ---------------------------------------------------------------------------
$KqlControls = @"
securityresources
| where type == 'microsoft.security/securescores/securescorecontrols'
| extend controlName = tostring(properties.displayName),
         unhealthy   = toint(properties.unhealthyResourceCount),
         current     = todouble(properties.score.current),
         max         = todouble(properties.score.max)
| where unhealthy > 0
| project subscriptionId, controlName, unhealthy, current, max
| order by unhealthy desc
"@

$KqlAssessments = @"
securityresources
| where type == 'microsoft.security/assessments'
| extend status = tostring(properties.status.code)
| where status == 'Unhealthy'
| extend rd = properties.resourceDetails
| extend assessment = tostring(properties.displayName),
         severity   = tostring(properties.metadata.severity),
         resourceId = tostring(coalesce(rd.Id, rd.id, rd.ResourceId, rd.resourceId))
| extend _parts = split(resourceId, '/')
| extend resourceName = tostring(_parts[array_length(_parts) - 1])
| extend sevRank = case(severity == 'High', 1, severity == 'Medium', 2, severity == 'Low', 3, 4)
| project subscriptionId, severity, sevRank, assessment, resourceName, resourceId, status
| order by sevRank asc
"@

$KqlIncidents = @"
SecurityIncident
| where TimeGenerated > ago(30d)
| summarize arg_max(TimeGenerated, Status, Severity) by IncidentNumber
| summarize open = countif(Status != 'Closed'), total = count() by Severity
"@

# ---------------------------------------------------------------------------
# 3. Helper: page through Resource Graph (>1000 rows)
# ---------------------------------------------------------------------------
function Invoke-Arg {
    param([string]$Query, [string[]]$Subs)
    $all = @(); $skip = $null
    do {
        $p = @{ Query = $Query; First = 1000 }
        if ($Subs)  { $p.Subscription = $Subs }
        if ($skip)  { $p.SkipToken    = $skip }
        $r    = Search-AzGraph @p
        $all += $r
        $skip = $r.SkipToken
    } while ($skip)
    return $all
}

# ---------------------------------------------------------------------------
# 4. Gather data
# ---------------------------------------------------------------------------
$subs = if ($SubscriptionId) { Get-AzSubscription | Where-Object Id -in $SubscriptionId }
        else                 { Get-AzSubscription | Where-Object State -eq 'Enabled' }
$subIds = $subs.Id

Write-Host "Querying $($subs.Count) subscription(s)..." -ForegroundColor Cyan

$ctrlRows   = Invoke-Arg -Query $KqlControls    -Subs $subIds
$assessRows = Invoke-Arg -Query $KqlAssessments -Subs $subIds

# Sentinel incidents (optional)
$incidents = @()
if ($SentinelWorkspaceId) {
    try {
        $q = Invoke-AzOperationalInsightsQuery -WorkspaceId $SentinelWorkspaceId -Query $KqlIncidents
        $incidents = foreach ($row in $q.Results) {
            [pscustomobject]@{ severity = $row.Severity; open = [int]$row.open; total = [int]$row.total }
        }
    } catch { Write-Warning "Sentinel query failed: $($_.Exception.Message)" }
}

# Per-subscription block
$subBlocks = foreach ($s in $subs) {
    Set-AzContext -SubscriptionId $s.Id | Out-Null

    # Secure score via REST (ascScore = the default Defender initiative)
    $cur = 0; $max = 0; $pct = 0
    try {
        $resp = Invoke-AzRestMethod -Method GET `
            -Path "/subscriptions/$($s.Id)/providers/Microsoft.Security/secureScores/ascScore?api-version=$ApiVersion"
        if ($resp.StatusCode -eq 200) {
            $score = ($resp.Content | ConvertFrom-Json).properties.score
            $cur = [math]::Round([double]$score.current, 1)
            $max = [double]$score.max
            $pct = if ($max -gt 0) { [math]::Round(100 * $cur / $max, 1) } else { 0 }
        }
    } catch { Write-Warning "Secure score unavailable for $($s.Name): $($_.Exception.Message)" }

    $ctrls = $ctrlRows | Where-Object subscriptionId -eq $s.Id | ForEach-Object {
        [pscustomobject]@{ name=$_.controlName; unhealthy=[int]$_.unhealthy; current=[double]$_.current; max=[double]$_.max }
    }
    $issues = $assessRows | Where-Object subscriptionId -eq $s.Id | ForEach-Object {
        [pscustomobject]@{ severity=$_.severity; assessment=$_.assessment; resourceName=$_.resourceName; resourceId=$_.resourceId; status=$_.status }
    }

    [pscustomobject]@{
        id=$s.Id; name=$s.Name; scorePct=$pct; current=$cur; max=$max; target=$TargetScorePct
        controls=@($ctrls); issues=@($issues)
    }
}

# Tenant-wide rollup (shown as "All subscriptions")
$totCur = ($subBlocks | Measure-Object current -Sum).Sum
$totMax = ($subBlocks | Measure-Object max     -Sum).Sum
$totPct = if ($totMax -gt 0) { [math]::Round(100 * $totCur / $totMax, 1) } else { 0 }

# ---------------------------------------------------------------------------
# 5. Assemble the JSON data model the HTML expects
# ---------------------------------------------------------------------------
$runId = (Get-Date -Format 'yyyyMMddHHmmss') + '-' + ([guid]::NewGuid().ToString('N').Substring(0,8))
$model = [pscustomobject]@{
    meta = [pscustomobject]@{
        period     = (Get-Date).ToString('MMMM yyyy')
        generated  = (Get-Date).ToString('yyyy-MM-dd HH:mm zzz')
        preparedBy = (Get-AzContext).Account.Id
    }
    overall = [pscustomobject]@{
        current = $totCur; max = $totMax; pct = $totPct
        lastPct = $totPct                     # TODO: read last month's value from your history store
        targetPct = $TargetScorePct
    }
    baselineNote = "Baseline target is a $TargetScorePct% secure score with zero open High-severity Sentinel incidents. Subscriptions below target require a documented remediation plan with named owners before sign-off."
    baselineControls = @(
        [pscustomobject]@{ name='Enable MFA';                target='100% — all privileged accounts enforced via Conditional Access' }
        [pscustomobject]@{ name='Secure management ports';   target='100% — no direct RDP/SSH from the internet; JIT or Bastion only' }
        [pscustomobject]@{ name='Remediate vulnerabilities'; target='No High-severity findings older than 30 days' }
        [pscustomobject]@{ name='Enable encryption at rest'; target='100% — storage / SQL using platform or CMK encryption' }
        [pscustomobject]@{ name='Enable Defender plans';     target='All production subscriptions onboarded' }
    )
    incidents     = @($incidents)
    subscriptions = @($subBlocks)
    runId         = $runId
}
$json = $model | ConvertTo-Json -Depth 8 -Compress

# ---------------------------------------------------------------------------
# 6. HTML template (single-quoted here-string = no PowerShell interpolation).
#    __REPORT_DATA__ is replaced with the live JSON below.
# ---------------------------------------------------------------------------
$template = @'
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monthly Security Posture Update</title><style>
:root{--bg:#0c1118;--panel:#121a24;--panel-2:#0f161f;--line:#1f2b38;--ink:#e6edf3;--muted:#8595a6;--faint:#5d6b7a;--accent:#2dd4bf;--accent-dim:#155e57;--high:#f0556d;--med:#f0a93b;--low:#4aa3ff;--ok:#2dd4bf;--high-bg:rgba(240,85,109,.12);--med-bg:rgba(240,169,59,.12);--low-bg:rgba(74,163,255,.12);--mono:ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);background-image:radial-gradient(900px 500px at 85% -10%,rgba(45,212,191,.06),transparent 60%);-webkit-font-smoothing:antialiased;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding:32px 24px 80px}
header.top{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-end;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:22px}
.brand{display:flex;gap:14px;align-items:center}.glyph{width:42px;height:42px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),#0d9488);color:#021715;font-weight:800;font-size:20px}
h1{font-size:20px;margin:0;letter-spacing:-.01em}.sub{color:var(--muted);font-size:13px;margin-top:2px}
.meta-grid{display:flex;gap:26px;flex-wrap:wrap;font-size:12px}.meta-grid div span{display:block;color:var(--faint);text-transform:uppercase;letter-spacing:.08em;font-size:10px;margin-bottom:3px}.meta-grid div b{font-weight:600;font-family:var(--mono)}
.scope{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:22px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px}.scope label{font-size:11px;color:var(--faint);text-transform:uppercase;letter-spacing:.08em}.scope select{min-width:300px}.scope .scope-tag{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted)}
.hero{display:grid;grid-template-columns:auto 1fr;gap:34px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:28px 32px;margin-bottom:26px}
.gauge{--p:0;width:148px;height:148px;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--p)*1%),var(--line) 0);display:grid;place-items:center;position:relative}.gauge::after{content:"";position:absolute;inset:13px;border-radius:50%;background:var(--panel)}.gauge .val{position:relative;z-index:1;text-align:center}.gauge .val b{font-family:var(--mono);font-size:34px}.gauge .val small{display:block;color:var(--muted);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.hero-meta h2{margin:0 0 4px;font-size:14px;color:var(--muted);font-weight:600;letter-spacing:.04em;text-transform:uppercase}.hero-stats{display:flex;gap:34px;flex-wrap:wrap;margin-top:14px}.hero-stats .s b{font-family:var(--mono);font-size:24px;display:block}.hero-stats .s span{font-size:12px;color:var(--muted)}
.delta{font-family:var(--mono);font-size:13px;padding:3px 9px;border-radius:20px;font-weight:600}.delta.up{color:var(--ok);background:rgba(45,212,191,.12)}.delta.down{color:var(--high);background:var(--high-bg)}.delta.na{color:var(--faint);background:var(--panel-2)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:24px}.tab{appearance:none;background:none;border:0;color:var(--muted);font-family:var(--sans);font-size:14px;font-weight:600;padding:12px 18px;cursor:pointer;border-bottom:2px solid transparent}.tab:hover{color:var(--ink)}.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.panel{display:none}.panel.active{display:block}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:24px}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}.card .k{color:var(--faint);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.card .v{font-family:var(--mono);font-size:28px;margin-top:6px}
.section-h{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:26px 0 12px}.section-h h3{margin:0;font-size:15px}.section-h .hint{color:var(--faint);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}thead th{text-align:left;font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);padding:11px 14px;border-bottom:1px solid var(--line);font-weight:700;white-space:nowrap}tbody td{padding:11px 14px;border-bottom:1px solid var(--panel-2);vertical-align:top}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:var(--panel-2)}
.mono{font-family:var(--mono);font-size:12px;color:var(--muted)}.rid{font-family:var(--mono);font-size:11px;color:var(--faint);word-break:break-all;max-width:340px;display:inline-block}
.pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;font-family:var(--mono)}.pill.High{color:var(--high);background:var(--high-bg)}.pill.Medium{color:var(--med);background:var(--med-bg)}.pill.Low{color:var(--low);background:var(--low-bg)}.pill.ok{color:var(--ok);background:rgba(45,212,191,.12)}
.bar{height:6px;border-radius:6px;background:var(--line);overflow:hidden;min-width:90px}.bar>i{display:block;height:100%;background:var(--accent)}
.filters{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:16px}select,input[type=text],input[type=date]{background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:9px 12px;font-family:var(--sans);font-size:13px;outline:none}select:focus,input:focus{border-color:var(--accent-dim)}
.seg{display:flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}.seg button{appearance:none;background:var(--panel-2);border:0;color:var(--muted);padding:8px 13px;font-size:12px;font-weight:600;cursor:pointer}.seg button.active{background:var(--accent);color:#021715}.count{color:var(--faint);font-size:12px;margin-left:auto;font-family:var(--mono)}
.baseline-note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;padding:16px 18px;color:var(--muted);font-size:13px;margin-bottom:22px}.status-good{color:var(--ok)}.status-bad{color:var(--high)}.status-warn{color:var(--med)}
.signoff{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:26px 28px;max-width:760px}.signoff .row{display:grid;grid-template-columns:160px 1fr;gap:14px;align-items:center;margin-bottom:14px}.signoff .row label{color:var(--muted);font-size:13px}.signoff textarea{width:100%;min-height:90px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:11px;font-family:var(--sans);font-size:13px;resize:vertical}.signoff .actions{display:flex;gap:12px;margin-top:18px}.btn{appearance:none;border:0;border-radius:9px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer}.btn.primary{background:var(--accent);color:#021715}.btn.ghost{background:var(--panel-2);color:var(--ink);border:1px solid var(--line)}.evidence{font-size:12px;color:var(--faint);margin-top:18px;font-family:var(--mono)}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);color:var(--faint);font-size:11px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;font-family:var(--mono)}
@media print{body{background:#fff;color:#000}.tab,.seg,.filters,.btn{display:none!important}.panel{display:block!important}}
@media(max-width:680px){.hero{grid-template-columns:1fr;justify-items:center;text-align:center}.signoff .row{grid-template-columns:1fr}.scope select{min-width:200px}}
</style></head><body><div class="wrap">
<header class="top"><div class="brand"><div class="glyph">&#9960;</div><div><h1>Monthly Security Posture Update</h1><div class="sub">Defender for Cloud &middot; Microsoft Sentinel &middot; Azure Monitor</div></div></div>
<div class="meta-grid"><div><span>Reporting period</span><b id="m-period">&mdash;</b></div><div><span>Generated</span><b id="m-generated">&mdash;</b></div><div><span>Subscriptions</span><b id="m-subcount">&mdash;</b></div></div></header>
<div class="scope"><label for="sub-global">Viewing</label><select id="sub-global"></select><span class="scope-tag" id="scope-tag"></span></div>
<div class="hero"><div class="gauge" id="gauge"><div class="val"><b id="g-pct">&mdash;</b><small>Secure score</small></div></div>
<div class="hero-meta"><h2 id="hero-title">Secure score</h2><div class="hero-stats"><div class="s"><b id="g-current">&mdash;</b><span>Current points</span></div><div class="s"><b id="g-max">&mdash;</b><span>Max points</span></div><div class="s"><b><span class="delta" id="g-delta">&mdash;</span></b><span>vs. last month</span></div><div class="s"><b id="g-target" style="color:var(--accent)">&mdash;</b><span>Baseline target</span></div></div></div></div>
<div class="tabs"><button class="tab active" data-tab="baseline">Baseline</button><button class="tab" data-tab="risks">Current Risks</button><button class="tab" data-tab="signoff">Sign-off</button></div>
<section class="panel active" id="tab-baseline"><div class="baseline-note" id="baseline-note"></div><div class="section-h"><h3>Target posture vs. actual</h3><span class="hint">Green = at or above target</span></div><table><thead><tr><th>Subscription</th><th>Target score</th><th>Actual score</th><th>Status</th><th style="width:30%">Progress to target</th></tr></thead><tbody id="baseline-body"></tbody></table><div class="section-h"><h3>Control baselines</h3><span class="hint">Controls expected to be fully healthy</span></div><table><thead><tr><th>Control</th><th>Baseline expectation</th></tr></thead><tbody id="baseline-controls"></tbody></table></section>
<section class="panel" id="tab-risks"><div class="cards"><div class="card"><div class="k">High severity</div><div class="v" id="kpi-high" style="color:var(--high)">&mdash;</div></div><div class="card"><div class="k">Medium severity</div><div class="v" id="kpi-med" style="color:var(--med)">&mdash;</div></div><div class="card"><div class="k">Low severity</div><div class="v" id="kpi-low" style="color:var(--low)">&mdash;</div></div><div class="card"><div class="k">Open Sentinel incidents</div><div class="v" id="kpi-inc">&mdash;</div></div></div>
<div class="section-h"><h3>Controls losing the most points</h3><span class="hint" id="ctrl-scope">All subscriptions</span></div><table><thead><tr><th>Control</th><th>Subscription</th><th>Unhealthy resources</th><th>Score</th></tr></thead><tbody id="controls-body"></tbody></table>
<div class="section-h"><h3>Resources with issues</h3></div><div class="filters"><div class="seg" id="sev-seg"><button data-sev="all" class="active">All</button><button data-sev="High">High</button><button data-sev="Medium">Medium</button><button data-sev="Low">Low</button></div><input type="text" id="search" placeholder="Filter by resource or finding..." style="min-width:220px"><span class="count" id="issue-count"></span></div>
<table><thead><tr><th>Severity</th><th>Finding</th><th>Resource</th><th>Resource ID</th><th>Status</th></tr></thead><tbody id="issues-body"></tbody></table></section>
<section class="panel" id="tab-signoff"><div class="signoff"><div class="section-h" style="margin-top:0"><h3>Review &amp; sign-off</h3><span class="hint">For ISO 27001 / SOC 2 evidence</span></div><div class="row"><label>Reviewed by</label><input type="text" id="so-name" placeholder="Full name"></div><div class="row"><label>Role</label><input type="text" id="so-role" placeholder="e.g. Cloud Security Lead"></div><div class="row"><label>Date of review</label><input type="date" id="so-date"></div><div class="row"><label>Decision</label><select id="so-decision"><option>Accepted &mdash; posture within tolerance</option><option>Accepted with remediation actions</option><option>Escalated &mdash; outside risk tolerance</option></select></div><div class="row" style="align-items:flex-start"><label>Comments / actions</label><textarea id="so-comments" placeholder="Summary of decisions, agreed remediation owners and due dates..."></textarea></div><div class="actions"><button class="btn primary" onclick="window.print()">Save as PDF (print) for evidence</button><button class="btn ghost" onclick="document.querySelectorAll('#tab-signoff input,#tab-signoff textarea').forEach(function(e){e.value=''})">Clear</button></div><div class="evidence" id="evidence"></div></div></section>
<footer><span id="f-left"></span><span>Data source: Azure Resource Graph + Defender Secure Score API + Log Analytics</span></footer></div>
<script>
const REPORT_DATA = __REPORT_DATA__;
const D=REPORT_DATA,$=function(s){return document.querySelector(s)},el=function(t,c,h){var e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e};
const sevRank=function(s){return {High:1,Medium:2,Low:3}[s]||9};
const subById=function(id){return D.subscriptions.find(function(s){return s.id===id})};
var state={sub:"all",sev:"all",q:""};
function inScope(s){return state.sub==="all"||s.id===state.sub}
function scopedIssues(){var r=[];D.subscriptions.forEach(function(s){if(inScope(s))s.issues.forEach(function(i){r.push(Object.assign({},i,{sub:s.name}))})});return r}
function scopedControls(){var r=[];D.subscriptions.forEach(function(s){if(inScope(s))(s.controls||[]).forEach(function(c){r.push(Object.assign({},c,{sub:s.name}))})});return r}
function fixedMeta(){$("#m-period").textContent=D.meta.period;$("#m-generated").textContent=D.meta.generated;$("#m-subcount").textContent=D.subscriptions.length;$("#f-left").textContent="Run id: "+(D.runId||"-")+" \u00b7 generated locally";if(D.runId)$("#evidence").textContent="Run id: "+D.runId+" \u00b7 period "+D.meta.period+" \u00b7 "+D.meta.generated;}
function buildSelector(){var sel=$("#sub-global");sel.innerHTML="";sel.appendChild(new Option("All subscriptions  (rollup)","all"));D.subscriptions.forEach(function(s){sel.appendChild(new Option(s.name+"  \u2014  "+s.scorePct.toFixed(0)+"%",s.id))});}
function hero(){var cur,max,pct,target,delta,title;if(state.sub==="all"){var o=D.overall;cur=o.current;max=o.max;pct=o.pct;target=o.targetPct;delta=o.pct-(o.lastPct==null?o.pct:o.lastPct);title="All subscriptions";}else{var s=subById(state.sub);cur=s.current;max=s.max;pct=s.scorePct;target=s.target;delta=null;title=s.name;}
$("#hero-title").textContent="Secure score \u2014 "+title;$("#scope-tag").textContent=state.sub==="all"?D.subscriptions.length+" subscriptions":state.sub;$("#gauge").style.setProperty("--p",pct);$("#g-pct").textContent=pct.toFixed(0)+"%";$("#g-current").textContent=cur;$("#g-max").textContent=max;$("#g-target").textContent=(target||"-")+"%";var dl=$("#g-delta");if(delta===null){dl.textContent="n/a";dl.className="delta na";}else{dl.textContent=(delta>=0?"+":"")+delta.toFixed(1)+"%";dl.className="delta "+(delta>=0?"up":"down");}}
function baseline(){$("#baseline-note").textContent=D.baselineNote||"";var tb=$("#baseline-body");tb.innerHTML="";D.subscriptions.filter(inScope).forEach(function(s){var tgt=s.target||D.overall.targetPct||85,ok=s.scorePct>=tgt,warn=!ok&&s.scorePct>=tgt-10;var cls=ok?"status-good":(warn?"status-warn":"status-bad"),label=ok?"On target":(warn?"Near target":"Below target");var pct=Math.min(100,Math.round(s.scorePct/tgt*100));var r=el("tr");r.innerHTML="<td><b>"+s.name+"</b><div class='mono'>"+s.id+"</div></td><td class='mono'>"+tgt+"%</td><td class='mono "+cls+"'>"+s.scorePct.toFixed(1)+"%</td><td class='"+cls+"'>\u25cf&nbsp;"+label+"</td><td><div class='bar'><i style='width:"+pct+"%;background:"+(ok?'var(--ok)':'var(--med)')+"'></i></div></td>";tb.appendChild(r);});var cb=$("#baseline-controls");cb.innerHTML="";(D.baselineControls||[]).forEach(function(c){var r=el("tr");r.innerHTML="<td><b>"+c.name+"</b></td><td class='mono' style='color:var(--muted)'>"+c.target+"</td>";cb.appendChild(r);});}
function kpis(){var iss=scopedIssues();$("#kpi-high").textContent=iss.filter(function(i){return i.severity==="High"}).length;$("#kpi-med").textContent=iss.filter(function(i){return i.severity==="Medium"}).length;$("#kpi-low").textContent=iss.filter(function(i){return i.severity==="Low"}).length;$("#kpi-inc").textContent=(D.incidents||[]).reduce(function(a,i){return a+(i.open||0)},0);}
function controlsTable(){var tb=$("#controls-body");tb.innerHTML="";var rows=scopedControls().sort(function(a,b){return b.unhealthy-a.unhealthy});$("#ctrl-scope").textContent=state.sub==="all"?"All subscriptions":((subById(state.sub)||{}).name||"");if(!rows.length){tb.innerHTML="<tr><td colspan='4' class='mono' style='color:var(--faint)'>No controls losing points.</td></tr>";return;}rows.forEach(function(c){var r=el("tr");r.innerHTML="<td><b>"+c.name+"</b></td><td class='mono'>"+c.sub+"</td><td><span class='pill High'>"+c.unhealthy+"</span></td><td class='mono'>"+(+c.current).toFixed(1)+" / "+c.max+"</td>";tb.appendChild(r);});}
function issuesTable(){var tb=$("#issues-body");tb.innerHTML="";var rows=scopedIssues().filter(function(i){return (state.sev==="all"||i.severity===state.sev)&&(state.q===""||(i.assessment+" "+i.resourceName).toLowerCase().indexOf(state.q)>=0)});rows.sort(function(a,b){return sevRank(a.severity)-sevRank(b.severity)});$("#issue-count").textContent=rows.length+" finding"+(rows.length===1?"":"s");if(!rows.length){tb.innerHTML="<tr><td colspan='5' class='mono' style='color:var(--faint)'>No matching findings.</td></tr>";return;}rows.forEach(function(i){var r=el("tr");r.innerHTML="<td><span class='pill "+i.severity+"'>"+i.severity+"</span></td><td>"+i.assessment+"<div class='mono'>"+i.sub+"</div></td><td><b>"+i.resourceName+"</b></td><td><span class='rid'>"+i.resourceId+"</span></td><td><span class='pill "+(i.status==='Unhealthy'?'High':'ok')+"'>"+i.status+"</span></td>";tb.appendChild(r);});}
function render(){hero();baseline();kpis();controlsTable();issuesTable();}
document.querySelectorAll(".tab").forEach(function(t){t.addEventListener("click",function(){document.querySelectorAll(".tab").forEach(function(x){x.classList.remove("active")});document.querySelectorAll(".panel").forEach(function(x){x.classList.remove("active")});t.classList.add("active");$("#tab-"+t.dataset.tab).classList.add("active");});});
$("#sub-global").addEventListener("change",function(e){state.sub=e.target.value;render();});
$("#search").addEventListener("input",function(e){state.q=e.target.value.trim().toLowerCase();issuesTable();});
$("#sev-seg").addEventListener("click",function(e){if(e.target.tagName!=="BUTTON")return;$("#sev-seg").querySelectorAll("button").forEach(function(b){b.classList.remove("active")});e.target.classList.add("active");state.sev=e.target.dataset.sev;issuesTable();});
$("#so-date").value=new Date().toISOString().slice(0,10);
fixedMeta();buildSelector();render();
</script></body></html>
'@

# ---------------------------------------------------------------------------
# 7. Inject data and write the report
# ---------------------------------------------------------------------------
$html = $template.Replace('__REPORT_DATA__', $json)
$html | Out-File -FilePath $OutputPath -Encoding utf8
Write-Host "Report written to $OutputPath  (run id $runId)" -ForegroundColor Green

# Optional: upload as immutable audit evidence
if ($BlobContainerSas) {
    try {
        $blobUrl = $BlobContainerSas -replace '\?', "/posture-$($model.meta.period -replace ' ','-').html?"
        Invoke-RestMethod -Uri $blobUrl -Method Put -InFile $OutputPath `
            -Headers @{ 'x-ms-blob-type' = 'BlockBlob'; 'x-ms-blob-content-type' = 'text/html' }
        Write-Host "Uploaded to evidence store." -ForegroundColor Green
    } catch { Write-Warning "Upload failed: $($_.Exception.Message)" }
}
