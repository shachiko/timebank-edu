import sys
sys.path.insert(0, '.')
from app import app

client = app.test_client()

routes = ['/', '/login', '/register', '/noi-quy', '/skills', '/community']
langs = ['vi', 'en', 'zh', 'fr', 'de']

print('--- VERIFYING PUBLIC ROUTES ---')
for l in langs:
    client.get(f'/set-language/{l}', follow_redirects=True)
    for r in routes:
        res = client.get(r)
        assert res.status_code == 200, f'Route {r} failed for {l} with {res.status_code}'
        html = res.get_data(as_text=True)
        assert f'lang="{l}"' in html, f'Missing lang={l} in {r}'
print('All public routes rendered 200 OK across all 5 languages!')

print('--- VERIFYING ADMIN ROUTE ---')
client.post('/login', data={'ma_hoc_sinh': 'demo_quantruong', 'mat_khau': 'demo123'}, follow_redirects=True)
for l in langs:
    client.get(f'/set-language/{l}', follow_redirects=True)
    res = client.get('/admin')
    assert res.status_code == 200, f'/admin failed for {l}'
    html = res.get_data(as_text=True)
    assert f'lang="{l}"' in html, f'Missing lang={l} in /admin'
print('Admin route rendered 200 OK across all 5 languages!')
