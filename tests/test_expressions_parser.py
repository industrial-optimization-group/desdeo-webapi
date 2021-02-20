from utilities.expression_parser import numpify_expressions
import numpy as np
import numpy.testing as npt
import unittest


class TestNumpifyExpressions(unittest.TestCase):
    def test_numpify(self):
        expressions = ["x+y-z", "y+x", "z/x + 2*y"]
        variables = ["x", "y", "z"]

        numpified = numpify_expressions(expressions, variables)
        print(numpified[0])

        assert len(numpified) == 3

        xs = np.array([[1, 0, 0], [1, 1, 1], [2, 2, 2], [3, 3, 3], [0.5, 1.5, 2]])

        npt.assert_almost_equal(numpified[0](xs), np.array([1, 1, 2, 3, 0]))
        npt.assert_almost_equal(numpified[1](xs), np.array([1, 2, 4, 6, 2]))
        npt.assert_almost_equal(numpified[2](xs), np.array([0, 3, 5, 7, 7]))
