"""Publish only this repository's bridge and harmless pilot probe as prerelease assets."""
import base64
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

REPO = 'LegendaryGaoZheng/dreams-and-crusades-releases'


def api(method, path, value=None):
    data = json.dumps(value).encode() if value is not None else None
    req = urllib.request.Request('https://api.github.com/repos/'+REPO+'/'+path,
        data=data,method=method,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],
        'Accept':'application/vnd.github+json','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)


def main():
    assert os.environ['GITHUB_REPOSITORY'] == REPO
    commit = os.environ['GITHUB_SHA']
    tag = 'update-pilot-' + commit[:12]
    stage = Path(os.environ['RUNNER_TEMP'])/'dsh-update-pilot/bridge'
    jar = stage/'automodpack-mc1.21.1-neoforge-4.0.7-dsh1.jar'
    probe = (json.dumps({'project':'Dreams & Crusades','pilot_commit':commit})+'\n').encode()
    files = {jar.name:jar.read_bytes(),'update-probe.json':probe,'bridge-record.json':(stage/'record.json').read_bytes()}
    manifest = {'format':1,'repository':REPO,'version':tag,'files':[
        {'path':'kubejs/assets/dream_expedition/update-probe.json','size':len(probe),
         'sha1':hashlib.sha1(probe).hexdigest(),'sha256':hashlib.sha256(probe).hexdigest(),
         'url':f'https://github.com/{REPO}/releases/download/{tag}/update-probe.json'}]}
    files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    release = api('POST','releases',dict(tag_name=tag,target_commitish=commit,
        name='Incremental update pilot '+commit[:12],prerelease=True,draft=False,
        body='Experimental AutoModpack 4.0.7 D&C bridge dsh1. LGPL-3.0. Modified source is embedded in the JAR and available under bridge/. Original sources https://github.com/Skidamek/AutoModpack/tree/v4.0.7 . Test assets only; not a complete modpack release.'))
    upload = release['upload_url'].split('{')[0]
    assert urllib.parse.urlparse(upload).hostname=='uploads.github.com'
    for name,data in files.items():
        req=urllib.request.Request(upload+'?name='+urllib.parse.quote(name),data=data,method='POST',
          headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/octet-stream'})
        with urllib.request.urlopen(req,timeout=90) as r: json.load(r)
    root = {'format':1,'repository':REPO,'version':tag,'objects':{
        hashlib.sha1(probe).hexdigest():{'size':len(probe),'sha256':hashlib.sha256(probe).hexdigest(),
        'urls':[manifest['files'][0]['url']]}},
        'bootstrap':{'url':f'https://github.com/{REPO}/releases/download/{tag}/{jar.name}',
                     'sha256':hashlib.sha256(jar.read_bytes()).hexdigest()},
        'probe':manifest['files'][0]}
    try:
        current=api('GET','contents/update-sources.json')
        sha=current['sha']
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        sha=None
    body={'message':'Point experimental update sources at '+tag,
          'content':base64.b64encode((json.dumps(root,indent=2)+'\n').encode()).decode(),'branch':'main'}
    if sha:body['sha']=sha
    api('PUT','contents/update-sources.json',body)
    print(release['html_url'])


if __name__=='__main__':main()
