from sympy import symbols, lambdify
from typing import List
from sympy.parsing.sympy_parser import parse_expr
import numpy as np
import dill


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


if __name__ == "__main__":
    exprs = ["x+y", "z+x"]
    variables = ["x", "y", "z"]

    res = numpify_expressions(exprs, variables)
    dill.dumps(res)