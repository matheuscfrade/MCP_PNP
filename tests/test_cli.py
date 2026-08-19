import pytest

from mcp_pnp.cli import _parse_serve


def test_parse_serve_defaults(monkeypatch):
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    assert _parse_serve([]) == ("0.0.0.0", 8000)


def test_parse_serve_args_e_env(monkeypatch):
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")
    assert _parse_serve([]) == ("127.0.0.1", 9000)
    assert _parse_serve(["--host", "0.0.0.0", "--port", "8080"]) == ("0.0.0.0", 8080)


def test_parse_serve_desconhecido():
    with pytest.raises(SystemExit):
        _parse_serve(["--foo"])
