import unittest
from deterministic_formaliser.adapters.udpipe_adapter import _parse_conllu


class ConlluTests(unittest.TestCase):
    def test_parse(self):
        s = """# sent_id = 1
# text = John left.
1\tJohn\tJohn\tPROPN\tNNP\tNumber=Sing\t2\tnsubj\t_\t_
2\tleft\tleave\tVERB\tVBD\tTense=Past|VerbForm=Fin\t0\troot\t_\t_
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t_\t_

"""
        out = _parse_conllu(s)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].text, "John left.")
        self.assertEqual(out[0].tokens[1].lemma, "leave")
        self.assertEqual(out[0].tokens[1].feats["Tense"], "Past")


if __name__ == "__main__":
    unittest.main()
