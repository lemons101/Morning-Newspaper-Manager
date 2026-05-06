from pathlib import Path
from src.dashboard.view_model import build_dashboard_payload

runtime = Path('/root/projects/Morning-Newspaper-Manager/runtime')
payload = build_dashboard_payload(runtime)
print('HEADLINE:', payload.get('headline'))
print('\nLEAD:')
for x in payload.get('lead', [])[:3]:
    print('-', x.get('title'), '=>', x.get('summary'))
print('\nTOP STORIES:')
for s in payload.get('top_stories', [])[:3]:
    print('\n#', s.get('title'))
    print(s.get('summary'))
