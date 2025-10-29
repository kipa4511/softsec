import io
import sys
import json
import builtins
import pytest
import argparse
import types
import sys

import watermarking_utils
watermarking_utils.store_recipient_credentials = lambda *a, **kw: None
sys.modules["watermarking_utils"] = watermarking_utils

import watermarking_cli as cli


# -------------------- Helpers --------------------

def test_read_text_from_file(tmp_path):
    f = tmp_path / "secret.txt"
    f.write_text("hello")
    assert cli._read_text_from_file(str(f)) == "hello"


def test_read_text_from_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("data"))
    assert cli._read_text_from_stdin() == "data"


def test_read_text_from_stdin_empty(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with pytest.raises(ValueError):
        cli._read_text_from_stdin()


# -------------------- Secret/key resolution --------------------

def test_resolve_secret_priority(monkeypatch, tmp_path):
    args = argparse.Namespace(secret="abc", secret_file=None, secret_stdin=False)
    assert cli._resolve_secret(args) == "abc"

    f = tmp_path / "s.txt"
    f.write_text("file_secret")
    args = argparse.Namespace(secret=None, secret_file=str(f), secret_stdin=False)
    assert cli._resolve_secret(args) == "file_secret"

    monkeypatch.setattr(sys, "stdin", io.StringIO("stdin_secret"))
    args = argparse.Namespace(secret=None, secret_file=None, secret_stdin=True)
    assert cli._resolve_secret(args) == "stdin_secret"

    args = argparse.Namespace(secret=None, secret_file=None, secret_stdin=False)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "prompt_secret")
    assert cli._resolve_secret(args) == "prompt_secret"


def test_resolve_key_priority(monkeypatch, tmp_path):
    args = argparse.Namespace(key="abc", key_file=None, key_stdin=False, key_prompt=False)
    assert cli._resolve_key(args) == "abc"

    f = tmp_path / "k.txt"
    f.write_text("keydata\n")
    args = argparse.Namespace(key=None, key_file=str(f), key_stdin=False, key_prompt=False)
    assert cli._resolve_key(args) == "keydata"

    monkeypatch.setattr(sys, "stdin", io.StringIO("stdin_key\n"))
    args = argparse.Namespace(key=None, key_file=None, key_stdin=True, key_prompt=False)
    assert cli._resolve_key(args) == "stdin_key"

    args = argparse.Namespace(key=None, key_file=None, key_stdin=False, key_prompt=True)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "prompt_key")
    assert cli._resolve_key(args) == "prompt_key"

    args = argparse.Namespace(key=None, key_file=None, key_stdin=False, key_prompt=False)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "fallback_key")
    assert cli._resolve_key(args) == "fallback_key"


# -------------------- Subcommands --------------------

def test_cmd_methods(capsys):
    ret = cli.cmd_methods(argparse.Namespace())
    assert ret == 0
    out = capsys.readouterr().out
    assert isinstance(out, str)


def test_cmd_explore_stdout(monkeypatch, capsys):
    monkeypatch.setattr(cli, "explore_pdf", lambda x: {"a": 1})
    args = argparse.Namespace(input="x.pdf", out=None)
    ret = cli.cmd_explore(args)
    assert ret == 0
    assert json.loads(capsys.readouterr().out.strip()) == {"a": 1}


def test_cmd_explore_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "explore_pdf", lambda x: {"x": 2})
    out_file = tmp_path / "out.json"
    args = argparse.Namespace(input="in.pdf", out=str(out_file))
    ret = cli.cmd_explore(args)
    assert ret == 0
    assert json.loads(out_file.read_text()) == {"x": 2}


def test_cmd_embed_success(tmp_path, monkeypatch):
    out_file = tmp_path / "out.pdf"
    monkeypatch.setattr(cli, "_resolve_key", lambda a: "k")
    monkeypatch.setattr(cli, "_resolve_secret", lambda a: "s")
    monkeypatch.setattr(cli, "is_watermarking_applicable", lambda **kw: True)
    monkeypatch.setattr(cli, "apply_watermark", lambda **kw: b"PDFDATA")
    args = argparse.Namespace(
        input="in.pdf",
        output=str(out_file),
        method="toy-eof",
        position=None,
        key=None,
        secret=None,
    )
    ret = cli.cmd_embed(args)
    assert ret == 0
    assert out_file.exists()
    assert out_file.read_bytes() == b"PDFDATA"


def test_cmd_embed_not_applicable(monkeypatch):
    monkeypatch.setattr(cli, "_resolve_key", lambda a: "k")
    monkeypatch.setattr(cli, "_resolve_secret", lambda a: "s")
    monkeypatch.setattr(cli, "is_watermarking_applicable", lambda **kw: False)
    args = argparse.Namespace(input="in.pdf", output="out.pdf", method="toy-eof", position=None)
    assert cli.cmd_embed(args) == 5


def test_cmd_extract_stdout(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_resolve_key", lambda a: "k")
    monkeypatch.setattr(cli, "read_watermark", lambda **kw: "secret_value")
    args = argparse.Namespace(input="file.pdf", out=None, method="toy-eof")
    ret = cli.cmd_extract(args)
    assert ret == 0
    assert "secret_value" in capsys.readouterr().out


def test_cmd_extract_to_file(tmp_path, monkeypatch):
    out_file = tmp_path / "secret.txt"
    monkeypatch.setattr(cli, "_resolve_key", lambda a: "k")
    monkeypatch.setattr(cli, "read_watermark", lambda **kw: "file_secret")
    args = argparse.Namespace(input="file.pdf", out=str(out_file), method="toy-eof")
    ret = cli.cmd_extract(args)
    assert ret == 0
    assert out_file.read_text() == "file_secret"


# -------------------- Parser / main --------------------

def test_build_parser_and_methods(monkeypatch):
    parser = cli.build_parser()
    args = parser.parse_args(["methods"])
    assert args.func == cli.cmd_methods


def test_main_success(monkeypatch):
    monkeypatch.setattr(cli, "cmd_methods", lambda a: 0)
    code = cli.main(["methods"])
    assert code == 0


@pytest.mark.parametrize(
    "exc,code",
    [
        (FileNotFoundError("no"), 2),
        (ValueError("bad"), 2),
        (cli.SecretNotFoundError("oops"), 3),
        (cli.InvalidKeyError("bad"), 4),
        (cli.WatermarkingError("fail"), 5),
    ],
)
def test_main_exceptions(monkeypatch, exc, code):
    def bad_func(_):
        raise exc
    args = argparse.Namespace(func=bad_func)
    monkeypatch.setattr(cli, "build_parser", lambda: argparse.ArgumentParser())
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self, x=None: args)
    assert cli.main([]) == code


def test_main_as_module(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda argv=None: 0)
    import importlib
    importlib.reload(cli)
