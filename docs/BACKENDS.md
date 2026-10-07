# Backend notes

## Why separate environments

The CLI has zero mandatory third-party dependencies. Each backend can live in its own virtual environment. This avoids forcing Stanza/PyTorch, spaCy, UDPipe native bindings and Trankit/Transformers into one dependency solution.

The main process launches the selected backend runner and receives only the common JSON analysis.

## Stanza

Setup:

```bash
python3.11 scripts/setup_backend.py stanza --lang en
```

The adapter requests tokenization, MWT expansion, POS, lemmatization and dependency parsing on CPU by default.

Official documentation:

- https://stanfordnlp.github.io/stanza/
- https://stanfordnlp.github.io/stanza/depparse.html

## spaCy

Setup:

```bash
python3.11 scripts/setup_backend.py spacy --lang en
```

Default English model: `en_core_web_sm`.

Override:

```bash
./deterministicFormaliser --parser spacy --spacy-model MODEL ...
```

spaCy's native dependency labels are preserved. The CNL renderer directly supports common labels such as `dobj`, `prep`, `pobj`, `nsubjpass` and `auxpass` in addition to UD-style labels.

Official documentation:

- https://spacy.io/
- https://spacy.io/usage/linguistic-features

## UDPipe

Setup for English:

```bash
python3.11 scripts/setup_backend.py udpipe --lang en
```

Python package: `ufal.udpipe`.

Official documentation:

- https://ufal.mff.cuni.cz/udpipe/1
- https://ufal.mff.cuni.cz/udpipe/1/models

The convenience English model downloaded by the script is an external UD 2.5 English-EWT model. It is not included in this project and its license is separate from the code license.

For arbitrary languages:

```bash
./deterministicFormaliser \
  --parser udpipe \
  --udpipe-model /path/to/model.udpipe \
  --lang xx \
  --mode analysis \
  --text "..."
```

## Trankit

Setup:

```bash
python3.11 scripts/setup_backend.py trankit --lang en
```

The setup script pins GitHub commit `54e863327391262cf72f6adc1b0ff104e972a1dc`, adapters 0.1.2, NumPy <2 and Hugging Face Hub <0.26. It installs CPU torch 2.0.1. The unconstrained dependency set failed locally because newer Transformers removed an imported AdamW API and disabled the older torch required by Trankit. Only dependency selection was changed; external parser code and weights were not edited.

Official project/documentation:

- https://github.com/nlp-uoregon/trankit
- https://trankit.readthedocs.io/

The installed stack uses CPU. `--gpu` requires a separately configured compatible GPU environment.

## Manual environments

If you already have a working backend environment, do not run the setup scripts. Point the CLI to it:

```bash
export DFORM_SPACY_PYTHON=/opt/spacy/bin/python
./deterministicFormaliser --parser spacy --mode cnl --text "..."
```

The referenced environment only needs the corresponding backend package/model. The runner imports the deterministicFormaliser source tree from this project.
