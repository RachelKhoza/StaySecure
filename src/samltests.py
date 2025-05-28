Successfully authenticates against the Jira API using API token and user credentials
		Can dynamically select and attach screenshots to a specific Xray Test Case using its issue key
	•	Screenshot is uploaded and visible in the “Attachments” section of the Jira Test Case
	•	GitHub Actions includes a separate reusable step for uploading screenshots to Jira
	•	Logs Jira API response status and includes retry mechanism for failures (max 3 retries)
	•	Secrets for Jira credentials are securely stored in GitHub Secrets and not hardcoded
	•	A dry-run mode is available for testing without making real API changes to Jira
	•	The upload step is reusable for different test cases and automatically maps test outputs
	•	Documented the setup steps and usage for the Jira Xray integration in the README.md
		Created a follow-up user story for syncing test results and statuses with Jira Xray