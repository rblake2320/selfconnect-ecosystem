"""Version identity must remain consistent across metadata and runtime headers."""

from __future__ import annotations

import importlib.metadata
import pathlib

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9-3.10
    import tomli as tomllib

from click.testing import CliRunner

from selfconnect import TskClient, __version__
from selfconnect.cli.main import cli
from selfconnect.langchain_handler import SelfConnectCallbackHandler


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_hatch_uses_runtime_version_file():
    config = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["dynamic"] == ["version"]
    assert config["tool"]["hatch"]["version"]["path"] == "selfconnect/_version.py"
    assert importlib.metadata.version("selfconnect") == __version__


def test_client_user_agent_uses_runtime_version():
    client = TskClient("sc-tsk-VERSION-TEST")
    try:
        assert client._http.headers["User-Agent"] == f"selfconnect-py/{__version__}"
    finally:
        client.close()


def test_cli_version_uses_distribution_version():
    result = CliRunner().invoke(cli, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_handler_session_metadata_uses_runtime_version(monkeypatch):
    import selfconnect.langchain_handler as module

    monkeypatch.setattr(module, "_LANGCHAIN_AVAILABLE", True)
    handler = object.__new__(SelfConnectCallbackHandler)
    handler.client = type(
        "Client",
        (),
        {"start_session": lambda self, agent_id, meta: "session-1"},
    )()
    handler.agent_id = "version-agent"
    handler.raise_on_error = True
    handler._session_id = None

    captured = {}

    def start_session(agent_id, meta):
        captured.update(agent_id=agent_id, meta=meta)
        return "session-1"

    handler.client.start_session = start_session
    handler._start_session()

    assert captured["agent_id"] == "version-agent"
    assert captured["meta"]["handler_version"] == __version__
