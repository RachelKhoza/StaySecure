
As a DevSecOps engineer
I want
	1.	Automated daily backups of DefectDojo
	2.	A weekly cleanup script to purge stale engagements
	3.	The DHH application onboarded with scheduled ZAP scans in lower environments
so that our security platform remains reliable, performant, and continuously tested.

Acceptance Criteria
	1.	Backup
	•	A script (dd_backup.sh) exists that dumps the Dojo PostgreSQL database and attachments to the agreed storage.
	•	A cron or GitLab-runner job runs the backup daily at 02:00 UTC and retains the last 7 days.
	•	A restore test in the test environment completes successfully.
	2.	Cleanup
	•	A Python script (dojo_cleanup.py) targets all projects and removes engagements older than 90 days.
	•	Script is parameterized (project list, age threshold) and idempotent.
	•	Scheduled weekly via cron/GitLab pipeline and logs summary to Slack/email.
	3.	DHH ZAP Integration
	•	“DHH Project” is created in DefectDojo with all lower-env URLs imported.
	•	ZAP context and policy files cover those URLs (including auth, if required).
	•	GitLab pipeline includes two jobs (zap-baseline, zap-full) that run against DHH lower-env.
	•	ZAP findings are automatically imported to the DHH engagement in DefectDojo via its API.
	•	A sample pipeline run completes with artifacts (ZAP report, Dojo findings) and no manual steps.