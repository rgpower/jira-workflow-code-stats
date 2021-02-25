import os
import requests
from dotenv import load_dotenv

load_dotenv()

jira_host = os.getenv('JIRA_ENDPOINT')
if not jira_host:
    raise Exception("no host configured for jira")

jira_creds = os.getenv('JIRA_CREDENTIALS')
if not jira_creds:
    raise Exception("no credentials for jira")
jira_up = tuple(jira_creds.split(":"))


def jira_request(path, data=None, json=None, params=None, method='post', **kwargs):
    response = requests.request(
        method, f"{jira_host}{path}", data=data, json=json, **kwargs, params=params, auth=jira_up)

    if response.status_code >= 400:
        raise Exception(f"Jira responded with status code: {response.status_code}")

    return response


def paged_jira_request(cb, path, json=None, params=None, method='post', **kwargs):
    start_at = 0
    done = False
    while not done:
        if json:
            json["startAt"] = start_at
        else:
            if params:
                params['startAt'] = start_at
                if 'maxResults' not in params:
                    params['maxResults'] = 100
            else:
                params = {'startAt': start_at, 'maxResults': 100}

        response = requests.request(
            method, f"{jira_host}{path}", json=json, **kwargs, params=params, auth=jira_up)

        if response.status_code >= 400:
            raise Exception(f"Jira responded with status code: {response.status_code}")

        results = response.json()

        start_at += cb(results, response)

        if start_at >= results['total']:
            done = True

# HACK
# got this from browser Dev Tools, Bitbucket uses GraphQL to load bitbucket info related to jira issue
# seems like it might eventually become a public api since it is not yet marked with internal path
# I copied at pasted the GraphQL payload as is, and mutate it just enough, to change the issue_id


def get_dev_details_payload(issue_id):
    data = '{"operationName":"DevDetailsDialog","query":"\\n    query DevDetailsDialog ($issueId: ID\u0021) {\\n        developmentInformation(issueId: $issueId){\\n            \\n    details {\\n        instanceTypes {\\n            id\\n            name\\n            type\\n            typeName\\n            isSingleInstance\\n            baseUrl\\n            devStatusErrorMessages\\n            repository {\\n                name\\n                avatarUrl\\n                description\\n                url\\n                parent {\\n                    name\\n                    url\\n                }\\n                branches {\\n        name\\n        url\\n        createReviewUrl\\n        createPullRequestUrl\\n        lastCommit {\\n            url\\n            displayId\\n            timestamp\\n        }\\n        pullRequests {\\n            name\\n            url\\n            status\\n            lastUpdate\\n        }\\n        reviews {\\n            state\\n            url\\n            id\\n        }\\n    }\\n                commits{\\n        id\\n        displayId\\n        url\\n        createReviewUrl\\n        timestamp\\n        isMerge\\n        message\\n        author {\\n          name\\n          avatarUrl\\n        }\\n        files{\\n          linesAdded\\n          linesRemoved\\n          changeType\\n          url\\n          path\\n        }\\n        reviews{\\n          id\\n          url\\n          state\\n        }\\n    }\\n                pullRequests {\\n        id\\n        url\\n        name\\n        branchName\\n        branchUrl\\n        lastUpdate\\n        status\\n        author {\\n          name\\n          avatarUrl\\n        }\\n        reviewers{\\n          name\\n          avatarUrl\\n          isApproved\\n        }\\n    }\\n            }\\n            danglingPullRequests {\\n        id\\n        url\\n        name\\n        branchName\\n        branchUrl\\n        lastUpdate\\n        status\\n        author {\\n          name\\n          avatarUrl\\n        }\\n        reviewers{\\n          name\\n          avatarUrl\\n          isApproved\\n        }\\n    }\\n            buildProviders {\\n          id\\n          name\\n          url\\n          description\\n          avatarUrl\\n          builds {\\n            id\\n            buildNumber\\n            name\\n            description\\n            url\\n            state\\n            testSummary {\\n              totalNumber\\n              numberPassed\\n              numberFailed\\n              numberSkipped\\n            }\\n            lastUpdated\\n            references {\\n              name\\n              uri\\n            }\\n          }\\n        }\\n         }\\n         deploymentProviders {\\n          id\\n          name\\n          homeUrl\\n          logoUrl\\n          deployments {\\n            displayName\\n            url\\n            state\\n            lastUpdated\\n            pipelineId\\n            pipelineDisplayName\\n            pipelineUrl\\n            environment {\\n                id\\n                type\\n                displayName\\n            }\\n          }\\n        }\\n         featureFlagProviders {\\n        id\\n        createFlagTemplateUrl\\n        linkFlagTemplateUrl\\n        featureFlags {\\n            id\\n            key\\n            displayName\\n            providerId\\n            details{\\n                url\\n                lastUpdated\\n                environment{\\n                    name\\n                    type\\n                }\\n                status{\\n                enabled\\n                defaultValue\\n                rollout{\\n                    percentage\\n                    text\\n                    rules\\n                }\\n            }\\n        }\\n    }\\n}\\n         remoteLinksByType {\\n        providers {\\n            id\\n            name\\n            homeUrl\\n            logoUrl\\n            documentationUrl\\n            actions {\\n                id\\n                label {\\n                    value\\n                }\\n                templateUrl\\n            }\\n        }\\n        types {\\n            type\\n            remoteLinks {\\n                id\\n                providerId\\n                displayName\\n                url\\n                type\\n                description\\n                status {\\n                    appearance\\n                    label\\n                }\\n                actionIds\\n                attributeMap {\\n                    key\\n                    value\\n                }\\n            }\\n        }\\n    }\\n         \\n    embeddedMarketplace {\\n        shouldDisplayForBuilds,\\n        shouldDisplayForDeployments,\\n        shouldDisplayForFeatureFlags\\n      }\\n\\n    }\\n\\n        }\\n    }","variables":{"issueId":"' + issue_id + '"}}'
    return data
