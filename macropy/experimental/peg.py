import re

from macropy.core.macros import *
from macropy.core.quotes import macros, q, u
from macropy.quick_lambda import macros, f
from macropy.case_classes import macros, case
from macropy.tracing import macros, show_expanded
import re
from collections import defaultdict
macros = Macros()

__all__ = ["Input", 'Parser', 'Success', 'Failure', 'cut', 'ParseError']

@macros.block()
def peg(tree, **kw):
    for statement in tree:
        if type(statement) is Assign:
            new_tree, bindings = _PegWalker.recurse_real(statement.value)
            statement.value = q(Parser.Lazy(lambda: ast(new_tree), [u%statement.targets[0].id]))

    return tree


@macros.expr()
def peg(tree, **kw):
    new_tree, bindings = _PegWalker.recurse_real(tree)
    return new_tree


@Walker
def _PegWalker(tree, ctx, stop, collect, **kw):
    if type(tree) is Str:
        stop()
        return q(Parser.Raw(ast(tree)))

    if type(tree) is BinOp and type(tree.op) is RShift:
        tree.left, b_left = _PegWalker.recurse_real(tree.left)
        tree.right = q(lambda bindings: ast(tree.right))
        tree.right.args.args = map(f(Name(id = _)), flatten(b_left))
        stop()
        return tree

    if type(tree) is BinOp and type(tree.op) is FloorDiv:
        tree.left, b_left = _PegWalker.recurse_real(tree.left)
        stop()
        collect(b_left)
        return tree

    if type(tree) is Tuple:
        result = q(Parser.Seq([]))

        result.args[0].elts = tree.elts
        all_bindings = []
        for i, elt in enumerate(tree.elts):
            result.args[0].elts[i], bindings = _PegWalker.recurse_real(tree.elts[i])
            all_bindings.append(bindings)
        stop()
        collect(all_bindings)
        return result

    if type(tree) is Compare and type(tree.ops[0]) is Is:
        left_tree, bindings = _PegWalker.recurse_real(tree.left)
        new_tree = q(ast(left_tree).bind_to(u(tree.comparators[0].id)))
        stop()
        collect(bindings + [tree.comparators[0].id])
        return new_tree

"""
PEG Parser Atoms
================
Sequence: e1 e2             ,   8       Seq
Ordered choice: e1 / e2     |   7       Or
Zero-or-more: e*            ~   13      Rep
One-or-more: e+             +   13      rep1
Optional: e?                            opt
And-(predicate: &e           &   9       And
Not-predicate: !e           -   13      Not
"""

cut = object()

@case
class Input(string, index):
    pass


@case
class Success(output, bindings, remaining_input):
    pass


@case
class Failure(remaining_input, failed, fatal | False):
    @property
    def index(self):
        return self.remaining_input.index
    @property
    def trace(self):
        print [f.trace_name for f in self.failed]
        return [x for f in self.failed for x in f.trace_name]


class ParseError(Exception):
    def __init__(self, failure):
        self.failure = failure
        line_length = 60

        string = self.failure.remaining_input.string
        index = self.failure.index
        line_start = string.rfind('\n', 0, index+1)

        line_end = string.find('\n', index+1, len(string))
        if line_end == -1:
            line_end = len(string)

        line_num = string.count('\n', 0, index)

        offset = min(index - line_start , 40)

        msg = "index: " + str(failure.index) + ", line: " + str(line_num + 1) + ", col: " + str(index - line_start) + "\n" + \
              " / ".join([x for f in failure.failed for x in f.trace_name]) + "\n" + \
              string[line_start+1:line_end][index - offset - line_start:index+line_length-offset - line_start] + "\n" + \
              (offset-1) * " " + "^"

        Exception.__init__(self, msg)

@case
class Parser:

    def bind_to(self, string):
        return Parser.Binder(self, string)

    def parse_partial(self, string):
        return self.parse_input(Input(string, 0))

    def parse_string(self, string):
        return Parser.Full(self).parse_input(Input(string, 0))

    def parse(self, string):
        res = Parser.Full(self).parse_input(Input(string, 0))
        if type(res) is Success:
            return res.output
        else:
            raise ParseError(res)

    @property
    def trace_name(self):
        return []

    def parse_input(self, input):
        """
        input: Input -> success: (results: T, results_dict: dict, new_input: Input)
                     -> failure: (index: int, failed: Parser, fatal: boolean)
        """

    def __and__(self, other):   return Parser.And([self, other])

    def __or__(self, other):    return Parser.Or([self, other])

    def __neg__(self):          return Parser.Not(self)

    @property
    def rep1(self):
        return Parser.And([Parser.Rep(self), self])

    @property
    def rep(self):
        return Parser.Rep(self)

    @property
    def opt(self):
        return Parser.Or([self, Parser.Raw("")])

    @property
    def r(self):
        """Creates a regex-matching parser from the given raw parser"""
        return Parser.Regex(self.string)
    def __mul__(self, n):   return Parser.RepN(self, n)

    def __floordiv__(self, other):   return Parser.Transform(self, other)

    def __pow__(self, other):   return Parser.Transform(self, lambda x: other(*x))

    def __rshift__(self, other): return Parser.TransformBound(self, other)


    class Full(parser):
        def parse_input(self, input):
            res = self.parser.parse_input(input)
            if type(res) is Success and res.remaining_input.index < len(input.string):
                return Failure(res.remaining_input, [self])
            else:
                return res



    class Raw(string):
        def parse_input(self, input):
            if input.string[input.index:].startswith(self.string):
                return Success(self.string, {}, input.copy(index = input.index + len(self.string)))
            else:
                return Failure(input, [self])

    class Regex(regex_string):
        def parse_input(self, input):
            match = re.match(self.regex_string, input.string[input.index:])
            if match:
                group = match.group()
                return Success(group, {}, input.copy(index = input.index + len(group)))
            else:
                return Failure(input, [self])


    class Seq(children):
        def parse_input(self, input):
            current_input = input
            results = []
            result_dict = defaultdict(lambda: [])
            committed = False
            for child in self.children:
                if child is cut:
                    committed = True
                else:
                    res = child.parse_input(current_input)


                    if type(res) is Failure:
                        if committed or res.fatal:
                            return Failure(res.remaining_input, [self] + res.failed, True)
                        else:
                            return res

                    current_input = res.remaining_input
                    results.append(res.output)
                    for k, v in res.bindings.items():
                        result_dict[k] = v

            return Success(results, result_dict, current_input)


    class Or(children):
        def parse_input(self, input):
            for child in self.children:
                res = child.parse_input(input)
                if type(res) is Success:
                    return res
                elif type(res) is Failure and res.fatal:
                    return res.copy(failed = [self] + res.failed)

            return Failure(input, [self])

    class And(children):
        def parse_input(self, input):
            results = [child.parse_input(input) for child in self.children]
            failures = [
                res for res in results
                if type(res) is Failure
            ]
            if failures == []:
                return results[0]
            else:
                return failures[0].copy(failed = [self] + failures[0].failed)


    class Not(parser):
        def parse_input(self, input):
            if type(self.parser.parse_input(input)) is Success:
                return Failure(input, [self])
            else:
                return Success(None, {}, input)


    class Rep(parser):
        def parse_input(self, input):
            current_input = input
            results = []
            result_dict = defaultdict(lambda: [])

            while True:
                res = self.parser.parse_input(current_input)
                if type(res) is Failure:
                    if res.fatal:
                        return res.copy(failed = [self] + res.failed)
                    else:
                        return Success(results, result_dict, current_input)

                current_input = res.remaining_input

                for k, v in res.bindings.items():
                    result_dict[k] = result_dict[k] + [v]

                results.append(res.output)


    class RepN(parser, n):
        def parse_input(self, input):
            current_input = input
            results = []
            result_dict = defaultdict(lambda: [])

            for i in range(self.n):
                res = self.parser.parse_input(current_input)
                if type(res) is Failure:
                    return res.copy(failed = [self] + res.failed)

                current_input = res.remaining_input

                for k, v in res.bindings.items():
                    result_dict[k] = result_dict[k] + [v]

                results.append(res.output)

            return Success(results, result_dict, current_input)

    class Transform(parser, func):

        def parse_input(self, input):
            res = self.parser.parse_input(input)
            if type(res) is Success:
                res.output = self.func(res.output)
                return res
            else:
                return res.copy(failed = [self] + res.failed)


    class TransformBound(parser, func):

        def parse_input(self, input):
            result = self.parser.parse_input(input)
            if type(result) is Success:

                return result.copy(output = self.func(**result.bindings), bindings={})

            else:
                return result.copy(failed = [self] + result.failed)

    class Binder(parser, name):
        def parse_input(self, input):
            result = self.parser.parse_input(input)
            if type(result) is Success:
                result.bindings[self.name] = result.output
                return result
            else:
                return result.copy(failed = [self] + result.failed)

    class Lazy(parser_thunk, trace_name):
        def parse_input(self, input):
            if not isinstance(self.parser_thunk, Parser):
                self.parser_thunk = self.parser_thunk()
            res = self.parser_thunk.parse_input(input)
            if type(res) is Success:
                return res
            else:
                return res.copy(failed = [self] + res.failed)


    class Succeed(string):
        def parse_input(self, input):
            return Success(self.string, {}, input)


    class Fail():
        def parse_input(self, input):
            return Failure(input, [self])






