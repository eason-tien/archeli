from __future__ import annotations


def test_system_monitor_endpoint_shape(client):
    resp = client.get('/v1/system/monitor')
    assert resp.status_code == 200
    body = resp.json()
    assert body['system'] == 'ArcHillx'
    assert 'host' in body
    assert 'ready' in body
    assert 'recovery' in body
    assert 'telemetry' in body
    assert 'timestamp' in body
