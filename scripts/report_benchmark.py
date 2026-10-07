#!/usr/bin/env python3
"""Aggregate recorded assistant judgments; never infer semantic success from coverage."""
import gzip
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "eval/benchmark"
sys.path.insert(0, str(ROOT / "src"))
from deterministic_formaliser.schema import Document


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-replay", action="store_true", help="Regenerate every archived CNL and compare with judged outputs")
    args = ap.parse_args()
    modules = {}
    replayed = 0
    summary, rows = [], []
    for file in sorted(DATA.glob("*-judged.json")):
        data = json.loads(file.read_text())
        parser, split, round_ = data["parser"], data["split"], data["round"]
        raw = gzip.decompress((DATA / f"{parser}-{split}-analyses.json.gz").read_bytes())
        assert hashlib.sha256(raw).hexdigest() == data["analysis_sha256"], file
        renderer = DATA / f"renderer-round-{round_}.py"
        assert hashlib.sha256(renderer.read_bytes()).hexdigest() == data["renderer_sha256"], file
        if args.verify_replay:
            if round_ not in modules:
                name = f"deterministic_formaliser._replay_round_{round_}"
                spec = importlib.util.spec_from_file_location(name, renderer)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                modules[round_] = module
            frozen = json.loads(raw)["rows"]
            for source, recorded in zip(frozen, data["rows"]):
                assert source["case"] == recorded["case"], file
                actual = modules[round_].render_cnl(Document.from_dict(source["document"])).to_dict()
                assert actual == recorded["output"], (file, source["case"]["id"])
                replayed += 1
        expected = 60 if split == "dev" else 20
        assert len(data["rows"]) == expected and len({r["case"]["id"] for r in data["rows"]}) == expected
        successes = sum(r["judgment"]["verdict"] == "success" for r in data["rows"])
        summary.append({"parser": parser, "split": split, "round": round_, "success": successes,
                        "total": expected, "rate": successes / expected})
        for row in data["rows"]:
            assert row["judgment"]["verdict"] in {"success", "failure", "uncertain"}
            output = row.get("output", {})
            rows.append({"parser": parser, "split": split, "round": round_, **row["case"],
                         "cnl": output.get("cnl", row.get("error", "")),
                         "coverage": output.get("coverage"), "warnings": output.get("warnings", []),
                         **row["judgment"]})
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    output = ROOT / "artifacts/benchmark/report.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    html = '''<!doctype html><html lang="ro"><meta charset="utf-8">
<title>Benchmark NL → CNL</title>
<style>body{font:15px system-ui;margin:28px;color:#182338;background:#f6f8fc}h1{font-size:26px}select,input{padding:8px;margin:5px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:12px;border-bottom:1px solid #dce1eb;vertical-align:top;text-align:left}th{position:sticky;top:0;background:#e9eef7}td:nth-child(2),td:nth-child(3){width:28%;white-space:pre-wrap}.success{color:#14713d}.failure{color:#b3261e}.uncertain{color:#865300}small{display:block;color:#526079;margin-top:7px}#stats{font-weight:bold;margin:15px 0}</style>
<h1>Benchmark NL → CNL · 80 de cazuri, 4 parsere, 5 runde</h1>
<p>Verdicte calitative date de asistent. Coverage nu este corectitudine semantică. Dev: 60 de cazuri folosite la corectare; holdout: 20 evaluate după înghețarea rundei 5. FRAGMENT și cazurile incerte nu sunt declarate formalizări reușite.</p>
<label>Set <select id="split"><option>holdout</option><option>dev</option></select></label>
<label>Runda <select id="round"><option>5</option><option>0</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
<label>Parser <select id="parser"><option value="">Toate</option><option>stanza</option><option>spacy</option><option>udpipe</option><option>trankit</option></select></label>
<label>Verdict <select id="verdict"><option value="">Toate</option><option>success</option><option>failure</option><option>uncertain</option></select></label>
<input id="query" placeholder="Caută caz, fenomen sau text" size="36"><div id="stats"></div>
<table><thead><tr><th>Caz / parser</th><th>NL original</th><th>CNL rezultat</th><th>Evaluare</th></tr></thead><tbody id="body"></tbody></table>
<script>const rows=PAYLOAD;
const ids=['split','round','parser','verdict','query'];
const el=id=>document.getElementById(id);
function render(){const selected=rows.filter(r=>r.split===el('split').value&&r.round===Number(el('round').value)&&(!el('parser').value||r.parser===el('parser').value)&&(!el('verdict').value||r.verdict===el('verdict').value)&&JSON.stringify(r).toLowerCase().includes(el('query').value.toLowerCase()));
el('stats').textContent=`${selected.length} rezultate afișate; ${selected.filter(r=>r.verdict==='success').length} reușite în selecție. Filtrarea după verdict nu definește rata benchmarkului.`;
el('body').replaceChildren();for(const r of selected){const tr=document.createElement('tr');for(const text of [r.id+' · '+r.parser+'\\n'+r.phenomenon,r.source,r.cnl]){const td=document.createElement('td');td.textContent=text;tr.append(td)}const td=document.createElement('td');const strong=document.createElement('strong');strong.textContent=r.verdict;strong.className=r.verdict;td.append(strong);const p=document.createElement('p');p.textContent=r.reason;td.append(p);const small=document.createElement('small');small.textContent='Coverage: '+(r.coverage??'N/A')+(r.attribution?' · Cauză: '+r.attribution:'')+(r.warnings.length?' · '+r.warnings.join('; '):'');td.append(small);tr.append(td);el('body').append(tr)}}
ids.forEach(id=>el(id).addEventListener('input',render));render();</script></html>'''.replace("PAYLOAD", payload)
    output.write_text(html)
    for row in sorted(summary, key=lambda x: (x["split"], x["round"], x["parser"])):
        print(f"{row['split']:7} R{row['round']} {row['parser']:7} {row['success']}/{row['total']} = {row['rate']:.1%}")
    print(output)
    if args.verify_replay:
        print(f"Exact replay verified: {replayed} recorded CNL results")


if __name__ == "__main__":
    main()
