import makeit.synthetic.evaluation.rexgen_direct.core_wln_global.mol_graph as mg
import makeit.synthetic.evaluation.rexgen_direct.core_wln_global.mol_graph_rich as mgr
import unittest
import numpy as np
import os
import sys
is_py2 = sys.version[0] == '2'
if is_py2:
    import cPickle as pickle
else:
    import pickle as pickle

class TestMolGraph(unittest.TestCase):
    def test_01_smiles2graph_list(self):
        np.set_printoptions(threshold=sys.maxsize)
        result = mg.smiles2graph_list(["c1cccnc1",'c1nccc2n1ccc2'])
        with open(os.path.join(os.path.dirname(__file__), 'expected/mg_smiles2graph_list.pkl'), 'rb') as t:
            expected = pickle.load(t)
        for e, r in zip(expected, result):
            self.assertTrue((e == r).all())

class TestMolGraphRich(unittest.TestCase):
    def test_01_smiles2graph_list(self):
        np.set_printoptions(threshold=sys.maxsize)
        result = mgr.smiles2graph_list(["c1cccnc1",'c1nccc2n1ccc2'])
        with open(os.path.join(os.path.dirname(__file__), 'expected/mgr_smiles2graph_list.pkl'), 'rb') as t:
            expected = pickle.load(t)
        for e, r in zip(expected, result):
            self.assertTrue((e == r).all())


if __name__ == '__main__':
    res = unittest.main(verbosity=3, exit=False)
