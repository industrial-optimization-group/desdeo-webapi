import json
from typing import List

import dill
import numpy as np
from sympy import lambdify, symbols
from sympy.parsing.sympy_parser import parse_expr


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
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


def recurse_check_lists_for_element_type(lst: list, types: tuple = (float, int)):
    # check if the items in a list lst are all of type types. Recursively descends into
    # sublists of lst
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
