# PULLING DATA FROM JIRA

I wrote this code to pull some information regarding the 'SI' project from Jira.

The CSV file noted above contains all issues that satisy this Jira query:

```
project = SI AND issuetype != Epic AND status = Done and development[commits].all > 0 order by created DESC
```

## CAVEATS

Note that in order to get the code-related metrics, like the number of repos, files, lines_added etc I used one of Atlassian's [non-documented
GraphQL api](jira/__init__.py).  For that reason, if you run this code in the future, you may have to modify it slightly, if Atlassian changes the way that
non-documented API works.

Atlassian supplies a Jira api, but since I was using a undocumented endpoint anyway, and only two other endpoints, I decided to
just go with using the simple python module [Requests: HTTP for Humans™](https://requests.readthedocs.io/) and the documentation for [Jira Cloud REST API v2](https://developer.atlassian.com/cloud/jira/platform/rest/v2/intro/).

## DATA CAPTURED

For each of the resolved as 'Done' issues in the SI project, I grabbed the following information:

name | value
:----|:-----
issue_id | numeric identifier of Jira issue
issue_key | pretty name of Jira issue
issue_type | type of Jira issue, Bug, Story etc...
date | Instant that the Jira ticket was first created
pipeline_count | number of BitBucket Pipeline runs associated with this issue
lines_added | total number of lines of code added per issue, across all files and repos
lines_removed | total number of lines of code removed per issue, across all files and repos
file_count | total number of files modified per issue, across all files and repos
branch_count | total number of branches per issue, across repos
repo_count | total number of repos per issue
component_count | total number of Jira components per issue
days_until_done | total number of days between creation of the Jira issue until resolved as 'Done'
days_until_released | total number of days between creation of the Jira issue until status set to 'released'
days_until_ready_for_system_testing | total number of days between issue creation and the last time the status set to 'Ready For System Testing'
days_until_first_ready_for_testing | total number of days between issue creation and the first time the status set to 'Ready For Testing'
days_until_in_progress | total number of days between issue creation and the first time the status set to 'In Progress'
days_until_first_assigned | total number of days between issue creation and the first time the status set to 'assigned'
comment_count | total number of comments associated with issue
attachment_count | total number of file attachments associated with issue
zendesk_tickets | total number of file attachments associated with issue
component_list | concatenated list of Jira components associated with issue
issue_summary | brief text description of Jira issue

## SAMPLE OUTPUT
Output should look like:

```
issue_id,issue_key,issue_type,date,pipeline_count,lines_added,lines_removed,file_count,branch_count,repo_count,component_count,days_until_done,days_until_released,days_until_ready_for_system_testing,days_until_first_ready_for_testing,days_until_in_progress,days_until_first_assigned,comment_count,attachment_count,zendesk_tickets,component_list,issue_summary
... rows...
```

## REQUIREMENTS

### PYTHON REQUIREMENTS

See [requirements.txt](requirements.txt) for a list of python packages required.

### JIRA API REQUIREMENTS

You will need to create a `.env` file that contains your Jira credentials and endpoint, similar to:

```
JIRA_CREDENTIALS=YourJiraUsername:YourJiraApiTokenHere
JIRA_ENDPOINT=https://YourCompany.atlassian.net
```

If you don't already have a Jira API Token, you could obtain one from [Atlassian account - API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

## FIRST RUN

Once you have your Atlassian API Token configured in your `.env` file, you should be able to do something like:
```
# first time only
$ python3 -mvenv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
# all requirements met

$ python main.py
```
Then in another terminal, you could check on the progress using something like:
```
tail -f output.csv
```

## TROUBLESHOOTING

### INVALID SYNTAX

Forgot to _source_ your `venv` environment

```
  File "main.py", line 122
    print(f'processing {issue["key"]}')
                                     ^
SyntaxError: invalid syntax
```

### MODULE NOT FOUND ERROR

Forgot to install the prerequsite modules via `pip install -r requirements.txt`
```
Traceback (most recent call last):
  File "main.py", line 1, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
```


### USE OF INCORRECT ATLASSIAN USERNAME

Supplied the wrong username

```
Traceback (most recent call last):
  File "main.py", line 264, in <module>
    summary({
  File "main.py", line 254, in summary
    paged_jira_request(issue_cb, "/rest/api/3/search", json=search_params)
  File "./jira/__init__.py", line 40, in paged_jira_request
    raise Exception(f"Jira responded with status code: {response.status_code}")
Exception: Jira responded with status code: 400
```

### USE OF INCORRECT ATLASSIAN API TOKEN

Supplied an incorrect (or no longer valid) API token
```
Traceback (most recent call last):
  File "main.py", line 264, in <module>
    summary({
  File "main.py", line 254, in summary
    paged_jira_request(issue_cb, "/rest/api/3/search", json=search_params)
  File "./jira/__init__.py", line 41, in paged_jira_request
    raise Exception(f"Jira responded with status code: {response.status_code}")
Exception: Jira responded with status code: 401
```
