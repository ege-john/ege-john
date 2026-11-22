"""Fetch actual contribution calendars, then regenerate the SVG. Standard library only."""
from pathlib import Path
import datetime as dt,json,os,urllib.request
from build_aurora import write_outputs

ROOT=Path(__file__).resolve().parents[1]
QUERY='''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}'''
LEVELS={'NONE':0,'FIRST_QUARTILE':1,'SECOND_QUARTILE':2,'THIRD_QUARTILE':3,'FOURTH_QUARTILE':4}

def fetch_snapshot(login,start_year,today,token,request=None):
    request=request or urllib.request.urlopen
    counts={};levels={};annual={}
    for year in range(start_year,today.year+1):
        start=dt.date(year,1,1);end=min(dt.date(year,12,31),today)
        payload={'query':QUERY,'variables':{'login':login,'from':start.isoformat()+'T00:00:00Z','to':end.isoformat()+'T23:59:59Z'}}
        req=urllib.request.Request('https://api.github.com/graphql',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'aurora-profile-updater'})
        with request(req,timeout=40) as response:body=json.load(response)
        if body.get('errors'):raise RuntimeError('GitHub GraphQL returned an error; cached data was not changed.')
        user=(body.get('data') or {}).get('user')
        if not user:raise RuntimeError('GitHub user could not be read; cached data was not changed.')
        cal=user['contributionsCollection']['contributionCalendar'];year_counts={}
        for week in cal['weeks']:
            for day in week['contributionDays']:
                date=dt.date.fromisoformat(day['date'])
                if not start<=date<=end:continue
                count=int(day['contributionCount'])
                if count<0:raise ValueError('Negative contribution count')
                year_counts[day['date']]=count
                levels[day['date']]=LEVELS[day['contributionLevel']]
        total=int(cal['totalContributions'])
        if sum(year_counts.values())!=total:raise RuntimeError('GitHub daily counts and annual total do not match; cached data was not changed.')
        counts.update(year_counts);annual[str(year)]=total
    return {'username':login,'as_of':today.isoformat(),'source':'github-graphql','total':sum(annual.values()),'annual_totals':annual,'daily_counts':counts,'daily_levels':levels}

def main():
    config=json.loads((ROOT/'data/config.json').read_text())
    token=os.environ.get('GITHUB_TOKEN')
    if not token:raise RuntimeError('GITHUB_TOKEN is required. In Actions it is supplied automatically.')
    login=os.environ.get('AURORA_USERNAME',config['username'])
    today=dt.datetime.now(dt.timezone.utc).date()
    data=fetch_snapshot(login,int(config['start_year']),today,token)
    # Build first. An API/build failure leaves the prior cached snapshot intact.
    write_outputs(data)
    path=ROOT/'data/contributions.json';temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2));temp.replace(path)
    print(f'Updated {login}: {data["total"]} contributions from {config["start_year"]} through {today.isoformat()}')

if __name__=='__main__':main()
