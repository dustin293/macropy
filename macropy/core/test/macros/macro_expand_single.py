from macropy.core.test.macros.basic_expr_macro import macros, g

def run():
    g = 10
    return g[1 * max(1, 2, 3)]
