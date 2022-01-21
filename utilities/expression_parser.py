from typing import List

import dill
import numpy as np
import simplejson as json
from sympy import lambdify, symbols
from sympy.parsing.sympy_parser import parse_expr
from pandas import DataFrame


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, DataFrame):
            return obj.to_json()
        if hasattr(obj, "__call__"):
            # do not serialize function objects
            if hasattr(obj, "__name__"):
                return obj.__name__
            else:
                return "Some non-serializable function object."
        return json.JSONEncoder.default(self, obj)


def numpify_expressions(expressions: List[str], variables: List[str]):
    # variables = ["x", "y", "z"]
    # exprs = ["x+y*z", "x-y/z"]

    # get variables
    xs = symbols(" ".join(variables))

    # parse the expressions
    syms = [parse_expr(expr) for expr in expressions]

    # make lambdas out of the functions
    functions = [lambdify(xs, f) for f in syms]

    # 'arrify' the lambdas to work with a single numpy array as
    # their input
    def arrify(fun):
        def f(x: np.ndarray, fun=fun):
            x = np.atleast_2d(x)
            return np.apply_along_axis(lambda y: fun(*y), 1, x)

        return f

    # arrify each of the parsed expressions and return the functions
    arrified_functions = list(map(arrify, functions))

    return arrified_functions


def recurse_check_lists_for_element_type(
    lst: list, types: tuple = (float, int)
) -> bool:
    # check if the items in a list lst are all of type types. Recursively descends into
    # sublists of lst
    """
    if not lst:
        return True
    elif isinstance(lst, list):
        return recurse_check_lists_for_element_type(
            lst[0] if len(lst) > 0 else []
        ) and recurse_check_lists_for_element_type(lst[1:] if len(lst) > 1 else [])
    elif isinstance(lst, types):
        return True
    else:
        return False
    """

    # assume that lists have all elements of the same type
    if not lst:
        return True
    elif len(lst) == 0:
        return True

    # descend into list
    for e1 in lst:
        # keep checking the first element of each sub list until a non-list is found
        if isinstance(e1, types):
            continue
        elif not isinstance(e1, list):
            return False

        for e2 in e1:
            if isinstance(e2, list):
                e1 = e2
                continue
            elif isinstance(e2, types):
                continue
            else:
                return False

    return True


def numpify_dict_items(dictionary: dict):
    # in the given dictionary, cast Python lists with numerical data to numpy arrays.
    # Leaves other items in the dictionary intact. Also leaves list with numpy incompatible dimensions intact
    new_dict = {
        (key): (
            np.array(value)
            if isinstance(value, list)
            and recurse_check_lists_for_element_type(value)
            and np.array(value).dtype != np.dtype("object")
            else value
        )
        for key, value in dictionary.items()
    }

    return new_dict


if __name__ == "__main__":
    exprs = ["x+y", "z+x"]
    variables = ["x", "y", "z"]

    res = numpify_expressions(exprs, variables)
    dill.dumps(res)
