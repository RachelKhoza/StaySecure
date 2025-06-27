---
- hosts: localhost
  connection: local
  gather_facts: no

  vars:
    jira_base: "https://your-domain.atlassian.net"
    src_testcase: "{{ testcase_to_clone }}"    # e.g. CORE-123
    jira_token: "{{ lookup('env','JIRA_API_TOKEN') }}"

  tasks:
    - name: Fail if no Jira token provided
      assert:
        that: jira_token is defined and jira_token | length > 0
        fail_msg: "Environment variable JIRA_API_TOKEN must be set"

    - name: Clone Xray Test Case {{ src_testcase }}
      uri:
        url: "{{ jira_base }}/rest/api/2/issue/{{ src_testcase }}/clone"
        method: POST
        headers:
          Authorization: "Bearer {{ jira_token }}"
          X-Atlassian-Token: "no-check"
          Content-Type: "application/json"
        body:
          fields:
            summary: "{{ src_testcase }} clone {{ lookup('pipe','date +%Y%m%d%H%M%S') }}"
        body_format: json
        status_code: 201
        return_content: yes
      register: clone

    - name: Extract new Test Case key
      set_fact:
        new_testcase_key: "{{ clone.json.key }}"

    - name: Create Xray Test Execution for the new Test Case
      uri:
        url: "{{ jira_base }}/rest/raven/1.0/api/testexec"
        method: POST
        headers:
          Authorization: "Bearer {{ jira_token }}"
          Content-Type: "application/json"
        body:
          info:
            summary: "Exec for {{ new_testcase_key }}"
            description: "Automated execution for {{ new_testcase_key }}"
            issuetype: "Test Execution"
          tests:
            - testKey: "{{ new_testcase_key }}"
        body_format: json
        status_code: 200,201
        return_content: yes
      register: exec

    - name: Extract new Test Execution key
      set_fact:
        new_execution_key: "{{ exec.json.testExecIssue.key }}"

    - name: Write output keys to JSON
      copy:
        dest: run_outputs.json
        content: |
          {
            "testcase": "{{ new_testcase_key }}",
            "execution": "{{ new_execution_key }}"
          }
        mode: '0644'

    - name: Display results
      debug:
        msg:
          - "🆕 Cloned Test Case: {{ new_testcase_key }}"
          - "🚀 Created Test Execution: {{ new_execution_key }}"