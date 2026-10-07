#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import venv

ROOT = Path(__file__).resolve().parents[1]

SPACY_MODELS = {
    "en": "en_core_web_sm", "de": "de_core_news_sm", "fr": "fr_core_news_sm",
    "es": "es_core_news_sm", "it": "it_core_news_sm", "pt": "pt_core_news_sm",
}
TRANKIT_LANG = {
    "en": "english", "de": "german", "fr": "french", "es": "spanish", "it": "italian",
    "pt": "portuguese", "ro": "romanian", "nl": "dutch", "pl": "polish", "cs": "czech",
}
UDPIPE_EN_URL = (
    "https://raw.githubusercontent.com/jwijffels/udpipe.models.ud.2.5/master/"
    "inst/udpipe-ud-2.5-191206/english-ewt-ud-2.5-191206.udpipe"
)


def run(cmd, **kwargs):
    print("+", " ".join(str(x) for x in cmd))
    subprocess.run([str(x) for x in cmd], check=True, **kwargs)


def vpython(env: Path) -> Path:
    p = env / "bin" / "python"
    if not p.exists():
        p = env / "Scripts" / "python.exe"
    return p


def create_env(name: str, recreate: bool, python: str | None = None) -> tuple[Path, Path]:
    env = ROOT / ".venvs" / name
    if recreate and env.exists():
        shutil.rmtree(env)
    if not env.exists():
        print(f"Creating {env}")
        if python:
            run([python, "-m", "venv", env])
        else:
            venv.EnvBuilder(with_pip=True).create(env)
    py = vpython(env)
    run([py, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    return env, py


def setup_stanza(py: Path, lang: str, no_model: bool):
    run([py, "-m", "pip", "install", "torch==2.14.1", "--index-url", "https://download.pytorch.org/whl/cpu"])
    run([py, "-m", "pip", "install", "-r", ROOT / "requirements/stanza.txt"])
    if not no_model:
        code = f"import stanza; stanza.download({lang!r}, processors='tokenize,mwt,pos,lemma,depparse', verbose=False)"
        run([py, "-c", code])


def setup_spacy(py: Path, lang: str, no_model: bool, model: str | None):
    run([py, "-m", "pip", "install", "-r", ROOT / "requirements/spacy.txt"])
    model = model or SPACY_MODELS.get(lang)
    if not no_model:
        if not model:
            raise SystemExit(f"No built-in spaCy model mapping for {lang!r}. Re-run with --spacy-model MODEL.")
        run([py, "-m", "spacy", "download", model])


def setup_udpipe(py: Path, lang: str, no_model: bool):
    run([py, "-m", "pip", "install", "-r", ROOT / "requirements/udpipe.txt"])
    if no_model:
        return
    model_dir = ROOT / "models" / "udpipe"
    model_dir.mkdir(parents=True, exist_ok=True)
    if lang != "en":
        raise SystemExit(
            "Automatic UDPipe model download is intentionally configured only for English. "
            "Download a compatible .udpipe model from the official UDPipe model repository and pass --udpipe-model PATH."
        )
    dest = model_dir / "en.udpipe"
    if not dest.exists():
        print("Downloading English EWT UDPipe model.")
        print("NOTE: this UD 2.5 model is distributed under CC BY-NC-SA; review the model license before commercial use.")
        temporary = dest.with_suffix(".udpipe.part")
        urllib.request.urlretrieve(UDPIPE_EN_URL, temporary)
        temporary.replace(dest)
    print(f"UDPipe model: {dest}")


def setup_trankit(py: Path, lang: str, no_model: bool):
    # The Trankit project currently recommends source installation when PyPI/model-server compatibility is problematic.
    run([py, "-m", "pip", "install", "torch==2.0.1", "--index-url", "https://download.pytorch.org/whl/cpu"])
    run([py, "-m", "pip", "install", "-r", ROOT / "requirements" / "trankit.txt"])
    if not no_model:
        package = TRANKIT_LANG.get(lang, lang)
        cache = ROOT / "models" / "trankit"
        cache.mkdir(parents=True, exist_ok=True)
        code = (
            "from trankit import Pipeline; "
            f"Pipeline({package!r}, gpu=False, cache_dir={str(cache)!r}); "
            "print('Trankit model ready')"
        )
        run([py, "-c", code])


def main():
    ap = argparse.ArgumentParser(description="Create an isolated virtual environment for one deterministicFormaliser backend.")
    ap.add_argument("backend", choices=["stanza", "spacy", "udpipe", "trankit"])
    ap.add_argument("--lang", default="en")
    ap.add_argument("--spacy-model")
    ap.add_argument("--no-model", action="store_true", help="Install package only; do not download a language model")
    ap.add_argument("--recreate", action="store_true")
    ap.add_argument("--python", help="Interpreter used to create the venv; Python 3.11 was validated for all four backends")
    args = ap.parse_args()

    _, py = create_env(args.backend, args.recreate, args.python)
    if args.backend == "stanza":
        setup_stanza(py, args.lang, args.no_model)
    elif args.backend == "spacy":
        setup_spacy(py, args.lang, args.no_model, args.spacy_model)
    elif args.backend == "udpipe":
        setup_udpipe(py, args.lang, args.no_model)
    elif args.backend == "trankit":
        setup_trankit(py, args.lang, args.no_model)
    print(f"\nReady: {args.backend}. The main CLI will auto-detect {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
