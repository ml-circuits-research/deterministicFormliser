.PHONY: test eval selftest setup-all smoke

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

eval:
	PYTHONPATH=src python3 scripts/eval_core.py

selftest:
	./scripts/selftest.sh

setup-all:
	./scripts/setup_all.sh en

smoke:
	./scripts/smoke_live.sh
