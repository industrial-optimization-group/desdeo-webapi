import unittest
import pytest

import numpy as np
import numpy.testing as npt
from utilities.expression_parser import (
    numpify_dict_items,
    numpify_expressions,
    recurse_check_lists_for_element_type,
)


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


@pytest.mark.parser
class TestNumpifyDictItems(unittest.TestCase):
    def test_1d(self):
        d = {"item_1": [10.2, 3.3, -1.2]}

        new_d = numpify_dict_items(d)

        # old list unchanged
        assert type(d["item_1"]) is list

        # new_d has numpy array in place of list
        assert type(new_d["item_1"]) is np.ndarray

        # dimension of array is 1
        assert new_d["item_1"].ndim == 1

        # items match between d and new_d
        npt.assert_almost_equal(new_d["item_1"], d["item_1"])

    def test_recurse_check(self):
        lst = [[1, 2, 3], [1.1, 2, 3.3], [1, -1, 2]]
        # ok
        assert recurse_check_lists_for_element_type(lst)

        lst = [["a", 2, 3], [1.1, 2, 3.3], [1, -1, 2]]
        # not ok
        assert not recurse_check_lists_for_element_type(lst)

        lst = [[1, 2, 3], [1.1, "b", 3.3], [1, -1, 2]]
        # not ok
        assert not recurse_check_lists_for_element_type(lst)

        lst = [[1, 2, 3], [1.1, 2, 3.3], [1, -1, "c"]]
        # not ok
        assert not recurse_check_lists_for_element_type(lst)

        lst = [[1, 2, 3], [1.1, 2, 3.3], ["c", -1, 2]]
        # not ok
        assert not recurse_check_lists_for_element_type(lst)

        lst = [[1, 2, 3], ["d", 2, 3.3], [1, -1, 2]]
        # not ok
        assert not recurse_check_lists_for_element_type(lst)

        lst = [
            [[1, 2, 3], [1.1, 2, 3.3], [1, -1, 2]],
            [[1, 2, 3], [1.1, 2, 3.3], [1, -1, 2]],
        ]
        # ok
        assert recurse_check_lists_for_element_type(lst)

    def test_2d(self):
        d = {"item_1": [[10.2, 3.3, -1.2], [-11.1, 12.2, -13.3333]]}

        new_d = numpify_dict_items(d)

        # old list unchanged
        assert type(d["item_1"]) is list

        # new_d has numpy array in place of list
        assert type(new_d["item_1"]) is np.ndarray

        # items match between d and new_d
        npt.assert_almost_equal(new_d["item_1"], d["item_1"])

    def test_edge_cases(self):
        # empty dict
        d = {}
        new_d = numpify_dict_items(d)

        assert new_d == {}

        # mixed values dict
        d = {
            "item_1": [[10.2, 3.3, -1.2], [-11.1, 12.2, -13.3333]],
            "item_2": ["I", "am", "a", "teapot"],
        }
        new_d = numpify_dict_items(d)

        npt.assert_almost_equal(new_d["item_1"], d["item_1"])
        assert new_d["item_2"] == d["item_2"]

        # no numerical values dict
        d = {
            "item_1": ["I", "am", "a", "teapot"],
            "item_2": ["I", "am", "also", "a", "teapot"],
        }
        new_d = numpify_dict_items(d)

        assert new_d["item_1"] == d["item_1"]
        assert new_d["item_2"] == d["item_2"]

        # mixed dims dict
        d = {
            "item_1": [
                [[1, 2, 3], [1.1, 2, 3.3], [1, -1, 2]],
                [[1, 2, 3], [1.1, 2, 3.3], [1, -1, 2]],
            ],
            "item_2": [[10.2, 3.3, -1.2], [-11.1, 12.2, -13.3333]],
            "item_3": [1, [1.1, 2.2], [2.2, 3.3, 4.4]],
        }
        new_d = numpify_dict_items(d)

        npt.assert_almost_equal(new_d["item_1"], d["item_1"])
        npt.assert_almost_equal(new_d["item_2"], d["item_2"])
        assert new_d["item_3"] == d["item_3"]

        # int and float elements and boolean
        d = {"item_1": 1, "item_2": 2.2, "item_3": True}
        new_d = numpify_dict_items(d)

        assert new_d["item_1"] == d["item_1"]
        assert new_d["item_2"] == d["item_2"]
        assert new_d["item_3"] == d["item_3"]
