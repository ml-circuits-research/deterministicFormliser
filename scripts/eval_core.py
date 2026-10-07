#!/usr/bin/env python3
"""Small dependency-free regression evaluation of the deterministic renderer.

This intentionally evaluates the renderer independently of parser quality. Live parser
comparison is done with smoke_live.sh after the four optional backends are installed.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deterministic_formaliser.schema import Document, Sentence, Token
from deterministic_formaliser.cnl import render_cnl


def T(i, text, lemma, upos, head, rel, feats=None):
    return Token(i, text, lemma, upos, "", feats or {}, head, rel)

CASES = [
    ("negation", "John did not send the report.", [
        T(1,"John","John","PROPN",4,"nsubj"), T(2,"did","do","AUX",4,"aux"),
        T(3,"not","not","PART",4,"neg"), T(4,"send","send","VERB",0,"root"),
        T(5,"the","the","DET",6,"det"), T(6,"report","report","NOUN",4,"obj"),
        T(7,".",".","PUNCT",4,"punct")], "ASSERT: John did not send the report."),
    ("question", "Did Alice approve the proposal?", [
        T(1,"Did","do","AUX",3,"aux"), T(2,"Alice","Alice","PROPN",3,"nsubj"),
        T(3,"approve","approve","VERB",0,"root"), T(4,"the","the","DET",5,"det"),
        T(5,"proposal","proposal","NOUN",3,"obj"), T(6,"?","?","PUNCT",3,"punct")],
        "ASK WHETHER: Alice did approve the proposal."),
    ("imperative", "Send the report to Mary.", [
        T(1,"Send","send","VERB",0,"root", {"Mood":"Imp"}), T(2,"the","the","DET",3,"det"),
        T(3,"report","report","NOUN",1,"obj"), T(4,"to","to","ADP",5,"case"),
        T(5,"Mary","Mary","PROPN",1,"obl"), T(6,".",".","PUNCT",1,"punct")],
        "COMMAND: Send the report to Mary."),
    ("causal", "John left because Mary arrived.", [
        T(1,"John","John","PROPN",2,"nsubj"), T(2,"left","leave","VERB",0,"root"),
        T(3,"because","because","SCONJ",5,"mark"), T(4,"Mary","Mary","PROPN",5,"nsubj"),
        T(5,"arrived","arrive","VERB",2,"advcl"), T(6,".",".","PUNCT",2,"punct")],
        "ASSERT: John left because Mary arrived."),
    ("passive", "The report was approved by Mary.", [
        T(1,"The","the","DET",2,"det"), T(2,"report","report","NOUN",4,"nsubj:pass"),
        T(3,"was","be","AUX",4,"aux:pass"), T(4,"approved","approve","VERB",0,"root"),
        T(5,"by","by","ADP",6,"case"), T(6,"Mary","Mary","PROPN",4,"obl"),
        T(7,".",".","PUNCT",4,"punct")], "ASSERT: The report was approved by Mary."),
]


def main():
    ok = 0
    for name, source, toks, expected in CASES:
        doc = Document("fixture", "en", source, [Sentence(1, source, toks)])
        got = render_cnl(doc).cnl
        passed = got == expected
        ok += int(passed)
        print(f"{name:12} {'PASS' if passed else 'FAIL'}  {got}")
        if not passed:
            print(f"  expected: {expected}")
    print(f"\ncore exact regression: {ok}/{len(CASES)} = {ok/len(CASES):.1%}")
    return 0 if ok == len(CASES) else 1

if __name__ == "__main__":
    raise SystemExit(main())
