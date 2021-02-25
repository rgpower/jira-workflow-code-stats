import requests
import os
import json
import math
import itertools
import pandas as pd

from dotenv import load_dotenv
from datetime import datetime
from functools import partial
from jira import paged_jira_request, jira_request, get_dev_details_payload
from utils import from_iso8601

load_dotenv()


def get_zendesk_tickets(issue_changes):
    zendesk_tickets = -1
    for issue_change in sorted(issue_changes, key=lambda e: e['created'], reverse=True):
        for item in reversed(issue_change['items']):
            if 'Zendesk Ticket Count' == item['field']:
                try:
                    zendesk_tickets = int(item['toString'])
                except ValueError:
                    pass
                break
        if zendesk_tickets > -1:
            break

    return 0 if zendesk_tickets < 0 else zendesk_tickets


def get_days_until_released(issue_changes, issue):
    issue_created = from_iso8601(issue['fields']['created'])
    days_until_released = math.nan
    if 'fixVersions' in issue['fields']:
        released_versions = filter(lambda fix_version: fix_version['released'], issue['fields']['fixVersions'])
        released_version = next(released_versions, None)
        if released_version is not None:
            release_date = datetime.fromisoformat(released_version['releaseDate'] + ' 00:00:00.000000+00:00')
            days_until_released = (release_date - issue_created).days
    return days_until_released


def _get_days_until_item_satisfies(issue_changes, issue, item_test, reverse):
    issue_created = from_iso8601(issue['fields']['created'])
    item_test_date = None
    for issue_change in sorted(issue_changes, key=lambda e: e['created'], reverse=reverse):
        for item in issue_change['items']:
            if item_test(item):
                item_test_date = from_iso8601(issue_change['created'])
                break
        if item_test_date is not None:
            break
    if item_test_date is None:
        return math.nan

    return (item_test_date - issue_created).days


def get_days_until_first_assigned(issue_changes, issue):
    def item_test(item): return 'assignee' == item['field'] and item['fromString'] is None
    days_until_first_assigned = _get_days_until_item_satisfies(issue_changes, issue, item_test, False)
    return days_until_first_assigned


def get_days_until_done(issue_changes, issue):
    def item_test(item): return 'resolution' == item['field'] and 'Done' == item['toString']
    days_until_done = _get_days_until_item_satisfies(issue_changes, issue, item_test, True)
    return days_until_done


def get_days_until_in_progress(issue_changes, issue):
    def item_test(item): return 'status' == item['field'] and 'In Progress' == item['toString']
    days_until_in_progress = _get_days_until_item_satisfies(issue_changes, issue, item_test, False)
    return days_until_in_progress


def get_days_until_first_ready_for_testing(issue_changes, issue):
    def item_test(item): return 'status' == item['field'] and 'Ready For Testing' == item['toString']
    days_until_first_ready_for_testing = _get_days_until_item_satisfies(issue_changes, issue, item_test, False)
    return days_until_first_ready_for_testing


def get_days_until_ready_for_system_testing(issue_changes, issue):
    def item_test(item): return 'status' == item['field'] and 'Ready For System Testing' == item['toString']
    days_until_ready_for_system_testing = _get_days_until_item_satisfies(issue_changes, issue, item_test, True)
    return days_until_ready_for_system_testing


def get_attachment_count(issue_changes):
    count = 0
    for issue_change in issue_changes:
        for item in issue_change['items']:
            if 'Attachment' == item['field']:
                count += 1
    return count


def get_comment_count(issue_changes):
    count = 0
    for issue_change in issue_changes:
        for item in issue_change['items']:
            if 'Comment' == item['field']:
                count += 1
    return count


def summary(search_params):
    rows = []
    file_hotspots = {}
    commit_hotspots = {}
    component_hotspots = {}

    def issue_cb(results, response):
        issue_count = len(results["issues"])
        for issue in results["issues"]:
            print(f'processing {issue["key"]}')
            issue_id = issue["id"]
            path = f'/rest/api/2/issue/{issue_id}/changelog'

            issue_changes = []

            def changelog_cb(results, response):
                values = results["values"]
                for value in values:
                    issue_changes.append(value)
                    items = value["items"]
                return len(values)

            paged_jira_request(changelog_cb, path, method='get', params={'maxResults': 10})

            pipeline_count = 0
            lines_added = 0
            lines_removed = 0
            file_count = 0
            branch_count = 0
            repo_count = 0

            deets_paload = get_dev_details_payload(issue_id)
            jh = {'Content-Type': 'application/json'}
            dev_details = jira_request("/jsw/graphql?operation=DevDetailsDialog", data=deets_paload, headers=jh).json()

            for it in dev_details['data']['developmentInformation']['details']['instanceTypes']:
                for repo in it['repository']:
                    repo_name = repo["name"]
                    repo_count += 1
                    for branch in repo['branches']:
                        branch_count += 1
                    for commit in repo['commits']:
                        if commit["isMerge"]:
                            continue
                        for f in commit['files']:
                            file_count += 1
                            lines_added += f["linesAdded"]
                            lines_removed += f["linesRemoved"]
                            hotspot_path = repo_name + ':' + f['path']
                            if hotspot_path in commit_hotspots:
                                commit_hotspots[hotspot_path] += 1
                            else:
                                commit_hotspots[hotspot_path] = 1
                            if hotspot_path in file_hotspots:
                                file_hotspots[hotspot_path] += (f["linesAdded"] + f["linesRemoved"])
                            else:
                                file_hotspots[hotspot_path] = (f["linesAdded"] + f["linesRemoved"])

            for dp in dev_details['data']['developmentInformation']['details']['deploymentProviders']:
                for deployment in dp['deployments']:
                    pipeline_count += 1

            component_names = []
            component_count = 0
            for component in issue['fields']['components']:
                component_names.append(component["name"])
                component_count += 1
                if component['name'] in component_hotspots:
                    component_hotspots[component['name']] += 1
                else:
                    component_hotspots[component['name']] = 1

            component_list = ";".join(component_names)

            days_until_done = get_days_until_done(issue_changes, issue)
            days_until_released = get_days_until_released(issue_changes, issue)
            days_until_ready_for_system_testing = get_days_until_ready_for_system_testing(issue_changes, issue)
            days_until_first_ready_for_testing = get_days_until_first_ready_for_testing(issue_changes, issue)
            days_until_in_progress = get_days_until_in_progress(issue_changes, issue)
            days_until_first_assigned = get_days_until_first_assigned(issue_changes, issue)
            zendesk_tickets = get_zendesk_tickets(issue_changes)
            comment_count = get_comment_count(issue_changes)
            attachment_count = get_attachment_count(issue_changes)

            rows.append({
                'issue_id': issue["id"],
                'issue_key': issue['key'],
                'issue_type': issue["fields"]["issuetype"]["name"],
                'date': from_iso8601(issue['fields']['created']).date(),
                'pipeline_count': pipeline_count,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'file_count': file_count,
                'branch_count': branch_count,
                'repo_count': repo_count,
                'component_count': component_count,
                'days_until_done': days_until_done,
                'days_until_released': days_until_released,
                'days_until_ready_for_system_testing': days_until_ready_for_system_testing,
                'days_until_first_ready_for_testing': days_until_first_ready_for_testing,
                'days_until_in_progress': days_until_in_progress,
                'days_until_first_assigned': days_until_first_assigned,
                'comment_count': comment_count,
                'attachment_count': attachment_count,
                'zendesk_tickets': zendesk_tickets,
                'component_list': f'<{component_list}>',
                'issue_summary': issue["fields"]["summary"],
            })

            df = pd.DataFrame(data=rows, columns=[
                'issue_id',
                'issue_key',
                'issue_type',
                'date',
                'pipeline_count',
                'lines_added',
                'lines_removed',
                'file_count',
                'branch_count',
                'repo_count',
                'component_count',
                'days_until_done',
                'days_until_released',
                'days_until_ready_for_system_testing',
                'days_until_first_ready_for_testing',
                'days_until_in_progress',
                'days_until_first_assigned',
                'comment_count',
                'attachment_count',
                'zendesk_tickets',
                'component_list',
                'issue_summary',
            ])

            df.to_csv('output.csv', index=False)

        return issue_count

    paged_jira_request(issue_cb, "/rest/api/3/search", json=search_params)

    hotspots = {
        'commits': commit_hotspots,
        'file': file_hotspots,
        'components': component_hotspots
    }
    print(json.dumps(hotspots, indent=True))


summary({
    'maxResults': 10,
    'jql': 'project = SI AND issuetype != Epic AND status = Done and development[commits].all > 0 order by created DESC'
})
