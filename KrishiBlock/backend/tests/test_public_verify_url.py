from app.config import normalize_public_url


def test_normalize_public_url_replaces_loopback_host(monkeypatch):
    monkeypatch.setattr('app.config.detect_lan_ip', lambda: '192.168.1.24')
    assert normalize_public_url('http://localhost:5173') == 'http://192.168.1.24:5173'


def test_normalize_public_url_keeps_public_host(monkeypatch):
    monkeypatch.setattr('app.config.detect_lan_ip', lambda: '192.168.1.24')
    assert normalize_public_url('https://krishiblock.example/verify') == 'https://krishiblock.example/verify'
