import keyring
import json
import re
import requests

def delete_excess_branches(repository, username='SirArthurTheSubmitter', organization='camelot-project'):
    S = requests.Session()
    S.headers['User-Agent']= 'camelot-project '+S.headers['User-Agent']
    kwargs = {'username': username, 'organization':organization, 'repository':repository}
    r = S.get('https://api.github.com/repos/{organization}/{repository}/pulls'.format(**kwargs),
              params={'state':'closed'})
    r.raise_for_status()

    results = json.loads(r.content)

    git_user = username
    password = keyring.get_password('github', git_user)

    for result in results:
        pullnumber = result['id']
        if result['state'] == 'closed':
            ref = result['head']['ref']
            print("Pruning pull {0} with title {1} and refid {2}".format(pullnumber, result['title'], ref))
            r = S.delete('https://api.github.com/repos/{organization}/{repository}/git/refs/heads/{ref}'.format(ref=ref, **kwargs),
                         auth=(git_user, password))
            if r.status_code == 204:
                # success
                continue
            d = json.loads(r.content)
            if d['message'] == 'Reference does not exist':
                print("Branch {0} seems to be already deleted.".format(ref))
                continue
            r.raise_for_status()
        else:
            print("Leaving unchanged pull {0} with title {1}".format(pullnumber, result['title']))
            raise Exception("This state should not be reachable if the API worked right ang gave us only closed PRs")

def close_pull_request(repository, pr_id, username='SirArthurTheSubmitter', organization='camelot-project',
                       delete_branch=True):
    S = requests.Session()
    S.headers['User-Agent']= 'camelot-project '+S.headers['User-Agent']

    kwargs = {'username': username, 'organization':organization, 'repository':repository}

    git_user = username
    password = keyring.get_password('github', git_user)

    S.post('https://api.github.com/repos/camelot-project/database/pulls/{0}'.format(pr_id),
           data=json.dumps({'state':'closed'}), auth=(git_user, password))

    response = S.get('https://api.github.com/repos/camelot-project/database/pulls/{0}'.format(pr_id))
    result = json.loads(response.content)

    if 'head' in result:
        ref = result['head']['ref']
        print("Pruning pull {0} with title {1} and refid {2}".format(pr_id, result['title'], ref))
        r = S.delete('https://api.github.com/repos/{organization}/{repository}/git/refs/heads/{ref}'.format(ref=ref, **kwargs),
                     auth=(git_user, password))
        print("Status code: ",r.status_code,".  204 means 'success', 422 means 'probably already deleted'")
    else:
        print("PR #{0} not found".format(pr_id))
