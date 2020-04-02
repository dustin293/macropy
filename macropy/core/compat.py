# -*- coding: utf-8 -*-

import ast
import logging
import sys

logger = logging.getLogger(__name__)

PY33 = sys.version_info >= (3, 3)
PY34 = sys.version_info >= (3, 4)
PY35 = sys.version_info >= (3, 5)
PY36 = sys.version_info >= (3, 6)
PY38 = sys.version_info >= (3, 8)

CPY = sys.implementation.name == 'cpython'
PYPY = sys.implementation.name == 'pypy'

HAS_FSTRING = CPY and PY36 or PYPY and PY35

if PY34:
    function_nodes = (ast.FunctionDef,)
else:
    function_nodes = (ast.AsyncFunctionDef, ast.FunctionDef)

scope_nodes = function_nodes + (ast.ClassDef,)


def arguments(*, posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
              kw_defaults=[], kwarg=None, defaults=[]):
    """A version of ``ast.arguments`` that deals with compatibility.

    The main reason for this was the introduction of ``posonlyargs``
    in Python 3.8.
    """
    if PY38:
        return ast.arguments(posonlyargs, args, vararg, kwonlyargs, kw_defaults,
                             kwarg, defaults)
    else:
        if posonlyargs:
            logger.warning("Positional only arguments merged with normal arguments"
            " because they are unsupported in this version of the interpreter. "
            "This may have negative implications.")
            args = posonlyargs + args
        return ast.arguments(args, vararg, kwonlyargs, kw_defaults, kwarg, defaults)


def Call(func, args, keywords):
    """A version of ``ast.Call`` that deals with compatibility.

    .. warning::

      Currently it supports only one element for each *args and **kwargs.
    """
    if PY35:
        return ast.Call(func, args, keywords)
    else:
        # see https://greentreesnakes.readthedocs.io/en/latest/nodes.html#Call
        starargs = [el.value for el in args if isinstance(el, ast.Starred)]
        if len(starargs) == 0:
            starargs = None
        elif len(starargs) == 1:
            starargs = starargs[0]
        else:
            raise ValueError("No more than one starargs.")
        kwargs = [el.value for el in keywords if el.arg is None]
        if len(kwargs) == 0:
            kwargs = None
        elif len(kwargs) == 1:
            kwargs = kwargs[0]
        else:
            raise ValueError("No more than one kwargs.")
        args = [el for el in args if not isinstance(el, ast.Starred)]
        keywords = [el for el in keywords if el.value is not kwargs]
        return ast.Call(func, args, keywords, starargs, kwargs)


def get_ast_const(tree):
    if PY38 and isinstance(tree, ast.Constant):
        return tree.value
    else:
        if isinstance(tree, ast.NameConstant):
            return tree.value
        elif isinstance(tree, ast.Str):
            return tree.s
        elif isinstance(tree, ast.Num):
            return tree.n


def is_ast_nameconst(tree):
    if PY38:
        return (isinstance(tree, ast.Constant) and
                (isinstance(tree.value, bool) or tree.value is None))
    else:
        return isinstance(tree, ast.NameConstant)


def is_ast_num(tree):
    if PY38:
        return (isinstance(tree, ast.Constant) and
                isinstance(tree.value, (int, float, complex)))
    else:
        return isinstance(tree, ast.Num)


def is_ast_str(tree):
    if PY38:
        return (isinstance(tree, ast.Constant) and
                isinstance(tree.value, str))
    else:
        return isinstance(tree, ast.Str)


def is_ast_const(tree):
    return any(test(tree) for test in [is_ast_nameconst, is_ast_num, is_ast_str])


def set_ast_const(tree, value):
    if PY38 and isinstance(tree, ast.Constant):
        tree.value = value
    else:
        if isinstance(tree, ast.NameConstant):
            tree.value = value
        elif isinstance(tree, ast.Str):
            tree.s = value
        elif isinstance(tree, ast.Num):
            tree.n = value
