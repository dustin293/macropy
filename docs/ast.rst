.. -*- coding: utf-8 -*-
.. :Project:   MacroPy3 -- AST wisdom
.. :Created:   gio 04 ott 2018 12:57:36 CEST
.. :Author:    Alberto Berti <alberto@metapensiero.it>
.. :License:   MIT
.. :Copyright: © 2018 Alberto Berti
..

.. _ast_primer:

An AST crash course
===================

The ``ast`` module of Python is greatly underdocumented: it does not
teach you anything of the contained node classes or how they are
expected to be used. What follows is some collected *wisdom* about
working with the AST classes, in the hope that you don't have to
repeat the same mistakes.


Third-party must read documentation
-----------------------------------

There is some other documentation on the web about the ``ast``
nodes. `Green Tree Snakes`__ is a *field guide*, it's invaluable
because it shows you how the nodes should be composed to create valid
AST *trees*.

__ https://greentreesnakes.readthedocs.io/


Use an AST pretty printer
-------------------------

AST nodes aren't your like your normal Python's standard library
object. Usually you are accustomed to work with objects that when
printed they tell you their features: this isn't true for AST
nodes. Let's see an example:

.. code:: python

  Python 3.6.6 (default, Jun 27 2018, 05:47:41)
  [GCC 7.3.0] on linux
  Type "help", "copyright", "credits" or "license" for more information.
  >>> from ast import parse
  >>> tree = parse('x = [x for x in range(5)]')
  >>> tree
  <_ast.Module object at 0x7f85c4464518>
  >>>

As you can see, the ``repr()`` of the ``tree`` variable doesn't tells
us much about what it represents. ``ast.dump()`` helps a bit:

.. code:: python

  >>> from ast import dump
  >>> dump(tree)
  "Module(body=[Assign(targets=[Name(id='x', ctx=Store())], value=ListComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Call(func=Name(id='range', ctx=Load()), args=[Num(n=5)], keywords=[]), ifs=[], is_async=0)]))])"

but not so much, we now can read all the expression that the *tree*
represents, but it isn't really so clear. To get a better printed
expression we can use one of the numerous AST pretty printers that are
available on PyPi: the meta_ package in my opinion does a good job, so
let's try it out:

.. _meta: http://srossross.github.io/Meta/html/

.. code:: console

  $ pip install meta
  $ python

.. code:: python

  Python 3.6.6 (default, Jun 27 2018, 05:47:41)
  [GCC 7.3.0] on linux
  Type "help", "copyright", "credits" or "license" for more information.
  >>> from ast import parse
  >>> from meta.asttools import print_ast
  >>> tree = parse('x = [x for x in range(5)]')
  >>> print_ast(tree)
  Module(body=[Assign(targets=[Name(ctx=Store(),
                                    id='x')],
                      value=ListComp(elt=Name(ctx=Load(),
                                              id='x'),
                                     generators=[comprehension(ifs=[],
                                                               is_async=0,
                                                               iter=Call(args=[Num(n=5)],
                                                                         func=Name(ctx=Load(),
                                                                                   id='range'),
                                                                         keywords=[]),
                                                               target=Name(ctx=Store(),
                                                                           id='x'))]))])
  >>>

As you can see using ``meta.asttools.print_ast()`` gives us a much
better understanding about how the tree is structured.

What if you fail to grasp what the AST tree stands for?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If with pretty printing the meaning of the AST tree is still obscure
to you, it's time to use MacroPy own helpers like ``unparse()``. Using
``tree`` from the last example:

.. code:: python

  >>> from macropy.core import unparse
  >>> unparse(tree)
  '\nx = [x for x in range(5)]'


``unparse()`` can convert back to Python source any AST tree of a
supported interpreter version.

AST node classes are picky and underdeveloped
---------------------------------------------

Yes, you read it right: AST node classes are picky and underdeveloped.

No simple way to create them
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For example the ``Name()`` nodes are used to store names: in variable
assignments they will be used to store the left side:

.. code:: python

  >>> from ast import parse
  >>> from meta.asttools import print_ast
  >>> tree = parse('x = 10')
  >>> print_ast(tree)
  Module(body=[Assign(targets=[Name(ctx=Store(),
                                    id='x')],
                      value=Num(n=10))])


However, when you try to create a ``Name`` object manually, you may
have some surprise:

.. code:: python

  >>> import ast
  >>> x = ast.Name('x')
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
  TypeError: Name constructor takes either 0 or 2 positional arguments

so no creation shortcuts. To create it you have to specify all the
positional arguments:

.. code:: python

  >>> x = ast.Name('x', ast.Store())

or find out the name of the fields and figure out the few needed:

.. code:: python

  >>> ast.Name._fields
  ('id', 'ctx')
  >>> x2 = ast.Name(id='x')

Always use a list where a sequence is needed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another example of this "pedantry" is when you try to recreate the
above assignment by hand:

.. code:: python

  >>> ass = ast.Assign(targets=(ast.Name(ctx=ast.Store(), id='x'),), value=ast.Num(n=10))
  >>> ass
  <_ast.Assign object at 0x7f85c3e377b8>
  >>>

This seems to work even if we used a tuple for the ``targets`` parameter, but
as soon as we try to run this code an error will surface:

.. code:: python

  >>> mod = ast.fix_missing_locations(ast.Module(body=[ass]))
  # ``mod`` and ``fix_missing_locations`` are needed when not using MacroPy
  >>> compile(mod, '<string>', 'exec')
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
  TypeError: Assign field "targets" must be a list, not a tuple

Instead, using a ``list``:

.. code:: python

  >>> ass = ast.Assign(targets=[ast.Name(ctx=ast.Store(), id='x')], value=ast.Num(n=10))
  >>> mod = ast.fix_missing_locations(ast.Module(body=[ass]))
  >>> compile(mod, '<string>', 'exec')
  <code object <module> at 0x7f85c3d88540, file "<string>", line 1>

Et voilà, the *tree* is compiled without errors.

So, always use a ``list`` instance where a sequence is expected!

There's no support for tree comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This may come as a surprise, but there's no support for rich
comparison between tree or even nodes:

.. code:: python

  >>> x = ast.Name(id='x')
  >>> x2 = ast.Name(id='x')
  >>> x == x2
  False

Even with more complex trees:

.. code:: python

  >>> ass = ast.Assign(targets=[ast.Name(ctx=ast.Store(), id='x')], value=ast.Num(n=10))
  >>> ass2 = ast.Assign(targets=[ast.Name(ctx=ast.Store(), id='x')], value=ast.Num(n=10))
  >>> ass3 = ast.Assign(targets=[ast.Name(ctx=ast.Store(), id='x')], value=ast.Num(n=11))
  # note that ``ass3`` assigns to 11
  >>> ass == ass2
  False
  >>> ass == ass3
  False

If you needed the package meta_ previously mentioned has a function
that helps here, let's see:

.. code:: python

  >>> from meta.asttools import cmp_ast
  >>> cmp_ast(x, x2)
  True
  >>> cmp_ast(ass, ass2)
  True
  >>> cmp_ast(ass, ass3)
  False

So don't expect any rich comparison using ``==`` operator, it will
behave like with two ``object()`` instances out of the box. If you
need it, use meta_ or build your own.
