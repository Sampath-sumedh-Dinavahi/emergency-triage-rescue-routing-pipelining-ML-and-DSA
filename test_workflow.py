import requests

# Reset
requests.post('http://localhost:5000/api/reset')

# Get all disasters
disasters = requests.get('http://localhost:5000/api/disasters').json()
print(f'Total disasters: {len(disasters)}')

# Print first 10 for inspection
for d in disasters[:15]:
    print(f'  {d["event_type"]:4s} {d["alert_level"]:8s} {d["country"][:20]:20s} {d["event_id"]}')

# Try to load each and dispatch until we get a successful dispatch
for d in disasters:
    requests.post('http://localhost:5000/api/reset')
    r = requests.post('http://localhost:5000/api/load-disaster', json={'event_type': d['event_type'], 'event_id': d['event_id']})
    if r.status_code != 200:
        continue
    state = requests.get('http://localhost:5000/api/state').json()
    if not state['edges']:
        continue
    print(f'\nLoaded: {d["event_type"]} {d["country"]} (id={d["event_id"]}) - {len(state["edges"])} edges, {len(state["emergencies"])} emergencies')
    
    # Try dispatching
    for i in range(10):
        r2 = requests.post('http://localhost:5000/api/dispatch')
        disp = r2.json()
        if disp['status'] == 'dispatched':
            risk = disp['risk_aware_route']
            norm = disp['normal_route']
            print(f'  SUCCESS! Dispatch {i+1}: {len(risk["coordinates"])} risk coords, {len(norm["coordinates"])} normal coords')
            print(f'  Risk first: {risk["coordinates"][0]}')
            print(f'  Routes differ: {disp["routes_differ"]}')
            print(f'  Use this event: type={d["event_type"]} id={d["event_id"]} country={d["country"]}')
            exit(0)
        elif disp['status'] == 'empty':
            print(f'  Queue empty after {i} dispatches')
            break

print('Could not find a working dispatch')
