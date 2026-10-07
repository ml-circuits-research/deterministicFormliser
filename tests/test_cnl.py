import unittest

from deterministic_formaliser.schema import Document, Sentence, Token
from deterministic_formaliser.cnl import render_cnl


def T(i, text, lemma, upos, head, rel, feats=None):
    return Token(i, text, lemma, upos, "", feats or {}, head, rel)


def render(text, tokens, strict=False):
    doc = Document("fixture", "en", text, [Sentence(1, text, tokens)])
    return render_cnl(doc, strict=strict)


class CNLTests(unittest.TestCase):
    def test_simple_negation(self):
        r = render("John did not send the report.", [
            T(1,"John","John","PROPN",4,"nsubj"),
            T(2,"did","do","AUX",4,"aux"),
            T(3,"not","not","PART",4,"neg"),
            T(4,"send","send","VERB",0,"root"),
            T(5,"the","the","DET",6,"det"),
            T(6,"report","report","NOUN",4,"obj"),
            T(7,".",".","PUNCT",4,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: John did not send the report.")
        self.assertEqual(r.coverage, 1.0)

    def test_modal_negation(self):
        r = render("Alice may not approve the proposal.", [
            T(1,"Alice","Alice","PROPN",4,"nsubj"),
            T(2,"may","may","AUX",4,"aux"),
            T(3,"not","not","PART",4,"neg"),
            T(4,"approve","approve","VERB",0,"root"),
            T(5,"the","the","DET",6,"det"),
            T(6,"proposal","proposal","NOUN",4,"obj"),
            T(7,".",".","PUNCT",4,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: Alice may not approve the proposal.")

    def test_condition_correct_ud(self):
        r = render("If Alice approves the proposal, Bob will deploy it.", [
            T(1,"If","if","SCONJ",3,"mark"),
            T(2,"Alice","Alice","PROPN",3,"nsubj"),
            T(3,"approves","approve","VERB",9,"advcl"),
            T(4,"the","the","DET",5,"det"),
            T(5,"proposal","proposal","NOUN",3,"obj"),
            T(6,",",",","PUNCT",3,"punct"),
            T(7,"Bob","Bob","PROPN",9,"nsubj"),
            T(8,"will","will","AUX",9,"aux"),
            T(9,"deploy","deploy","VERB",0,"root"),
            T(10,"it","it","PRON",9,"obj"),
            T(11,".",".","PUNCT",9,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: If Alice approves the proposal, Bob will deploy it.")
        self.assertEqual(r.coverage, 1.0)

    def test_yes_no_question(self):
        r = render("Did Alice approve the proposal?", [
            T(1,"Did","do","AUX",3,"aux"),
            T(2,"Alice","Alice","PROPN",3,"nsubj"),
            T(3,"approve","approve","VERB",0,"root"),
            T(4,"the","the","DET",5,"det"),
            T(5,"proposal","proposal","NOUN",3,"obj"),
            T(6,"?","?","PUNCT",3,"punct"),
        ])
        self.assertEqual(r.cnl, "ASK WHETHER: Alice did approve the proposal.")

    def test_wh_question(self):
        r = render("Why did Alice reject it?", [
            T(1,"Why","why","ADV",4,"advmod"),
            T(2,"did","do","AUX",4,"aux"),
            T(3,"Alice","Alice","PROPN",4,"nsubj"),
            T(4,"reject","reject","VERB",0,"root"),
            T(5,"it","it","PRON",4,"obj"),
            T(6,"?","?","PUNCT",4,"punct"),
        ])
        self.assertEqual(r.cnl, "ASK WHY: Alice did reject it.")
        self.assertEqual(r.coverage, 1.0)

    def test_imperative(self):
        r = render("Send the report to Mary.", [
            T(1,"Send","send","VERB",0,"root", {"Mood":"Imp"}),
            T(2,"the","the","DET",3,"det"),
            T(3,"report","report","NOUN",1,"obj"),
            T(4,"to","to","ADP",5,"case"),
            T(5,"Mary","Mary","PROPN",1,"obl"),
            T(6,".",".","PUNCT",1,"punct"),
        ])
        self.assertEqual(r.cnl, "COMMAND: Send the report to Mary.")

    def test_passive(self):
        r = render("The report was approved by Mary.", [
            T(1,"The","the","DET",2,"det"),
            T(2,"report","report","NOUN",4,"nsubj:pass"),
            T(3,"was","be","AUX",4,"aux:pass"),
            T(4,"approved","approve","VERB",0,"root"),
            T(5,"by","by","ADP",6,"case"),
            T(6,"Mary","Mary","PROPN",4,"obl"),
            T(7,".",".","PUNCT",4,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: The report was approved by Mary.")

    def test_copula(self):
        r = render("John is tired.", [
            T(1,"John","John","PROPN",3,"nsubj"),
            T(2,"is","be","AUX",3,"cop"),
            T(3,"tired","tired","ADJ",0,"root"),
            T(4,".",".","PUNCT",3,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: John is tired.")

    def test_causal_advcl(self):
        r = render("John left because Mary arrived.", [
            T(1,"John","John","PROPN",2,"nsubj"),
            T(2,"left","leave","VERB",0,"root"),
            T(3,"because","because","SCONJ",5,"mark"),
            T(4,"Mary","Mary","PROPN",5,"nsubj"),
            T(5,"arrived","arrive","VERB",2,"advcl"),
            T(6,".",".","PUNCT",2,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: John left because Mary arrived.")

    def test_coordination(self):
        r = render("John reviewed and approved the draft.", [
            T(1,"John","John","PROPN",2,"nsubj"),
            T(2,"reviewed","review","VERB",0,"root"),
            T(3,"and","and","CCONJ",4,"cc"),
            T(4,"approved","approve","VERB",2,"conj"),
            T(5,"the","the","DET",6,"det"),
            T(6,"draft","draft","NOUN",4,"obj"),
            T(7,".",".","PUNCT",2,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: John reviewed and approved the draft.")
        self.assertEqual(r.coverage, 1.0)

    def test_discourse_particle_is_preserved(self):
        r = render("Well, John left.", [
            T(1,"Well","well","INTJ",3,"discourse"),
            T(2,"John","John","PROPN",3,"nsubj"),
            T(3,"left","leave","VERB",0,"root"),
            T(4,".",".","PUNCT",3,"punct"),
        ])
        self.assertEqual(r.cnl, "ASSERT: Well, John left.")
        self.assertEqual(r.coverage, 1.0)

    def test_strict_rejects_loss(self):
        tokens = [
            T(1,"John","John","PROPN",2,"nsubj"),
            T(2,"left","leave","VERB",0,"root"),
            T(3,"yesterday","yesterday","ADV",2,"dep"),
            T(4,".",".","PUNCT",2,"punct"),
        ]
        with self.assertRaises(ValueError):
            render("John left yesterday.", tokens, strict=True)


if __name__ == "__main__":
    unittest.main()
