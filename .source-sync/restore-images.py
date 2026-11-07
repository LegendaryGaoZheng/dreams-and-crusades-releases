"""Materialize only the five reviewed source PNGs; never publish a game release."""
import base64, hashlib, json, os, urllib.request
REPO = 'LegendaryGaoZheng/dreams-and-crusades-releases'
assert os.environ['GITHUB_REPOSITORY'] == REPO
def api(method, path, value=None):
    body = json.dumps(value).encode() if value is not None else None
    request = urllib.request.Request('https://api.github.com/repos/'+REPO+'/'+path, data=body, method=method,
        headers={'Authorization': 'Bearer '+os.environ['GITHUB_TOKEN'], 'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response: return json.load(response)
head = api('GET', 'git/ref/heads/develop')['object']['sha']
assert head == os.environ['GITHUB_SHA'], 'Develop changed; refusing stale source import'
commit = api('GET', 'git/commits/'+head)
elements = []
for row in json.load(open('.source-sync/images.json', encoding='utf8')):
    assert row['path'].startswith('pack/kubejs/assets/dream_expedition/textures/quest_atlas/')
    assert row['path'].endswith('.png') and '..' not in row['path']
    data = base64.b64decode(row['base64'], validate=True)
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    blob = api('POST', 'git/blobs', {'content':row['base64'], 'encoding':'base64'})
    elements.append({'path':row['path'], 'mode':'100644', 'type':'blob', 'sha':blob['sha']})
assert len(elements) == 5
tree = api('POST', 'git/trees', {'base_tree':commit['tree']['sha'], 'tree':elements})
updated = api('POST', 'git/commits', {'message':'Restore reviewed quest atlas source images',
    'tree':tree['sha'], 'parents':[head]})
api('PATCH', 'git/refs/heads/develop', {'sha':updated['sha'], 'force':False})
print('Restored five reviewed PNG sources; no release published')
