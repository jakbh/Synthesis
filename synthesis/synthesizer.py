"""
Program Synthesis - Enumerative Synthesis over a simple DSL

Given input-output examples, this synthesizer searches through a
Domain-Specific Language (DSL) of arithmetic expressions to find
a program that satisfies all examples.

This is the classic "Programming by Example" (PBE) paradigm.
"""

from itertools import product


# --- DSL: arithmetic expression trees ---

class Var:
    """Represents the input variable x"""
    def eval(self, env):
        return env['x']
    def __repr__(self):
        return 'x'

class Const:
    """Represents an integer constant"""
    def __init__(self, n):
        self.n = n
    def eval(self, env):
        return self.n
    def __repr__(self):
        return str(self.n)

class Add:
    """Represents left + right"""
    def __init__(self, l, r):
        self.l, self.r = l, r
    def eval(self, env):
        return self.l.eval(env) + self.r.eval(env)
    def __repr__(self):
        return f'({self.l} + {self.r})'

class Mul:
    """Represents left * right"""
    def __init__(self, l, r):
        self.l, self.r = l, r
    def eval(self, env):
        return self.l.eval(env) * self.r.eval(env)
    def __repr__(self):
        return f'({self.l} * {self.r})'


# --- Enumerative search ---

def programs(depth, constants=(0, 1, 2, 3)):
    """Enumerate all programs in the DSL up to the given depth (size)."""
    if depth == 0:
        yield Var()
        for c in constants:
            yield Const(c)
    else:
        yield from programs(depth - 1, constants)
        for l, r in product(programs(depth - 1, constants), repeat=2):
            yield Add(l, r)
            yield Mul(l, r)


def synthesize(examples, max_depth=2):
    """
    Search for the smallest program satisfying all input-output examples.

    Args:
        examples: list of (input, output) pairs
        max_depth: maximum expression tree depth to search

    Returns:
        The first program found, or None if no program was found.
    """
    for depth in range(max_depth + 1):
        for prog in programs(depth):
            if all(prog.eval({'x': x}) == y for x, y in examples):
                return prog
    return None


# --- Demos ---

def demo(description, examples, max_depth=2):
    print(f"  Task   : {description}")
    print(f"  Examples: {examples}")
    prog = synthesize(examples, max_depth)
    if prog:
        print(f"  Synthesized: f(x) = {prog}")
    else:
        print("  No program found within search depth.")
    print()


if __name__ == '__main__':
    print("=== Program Synthesis: Programming by Example ===\n")
    print("Strategy: Enumerate all expression trees in a DSL smallest-first,")
    print("          return the first one consistent with all examples.\n")

    demo("f(x) = x + 2",  [(0, 2), (1, 3), (2, 4), (5, 7)])
    demo("f(x) = 2 * x",  [(0, 0), (1, 2), (2, 4), (3, 6)])
    demo("f(x) = x * x",  [(0, 0), (1, 1), (2, 4), (3, 9)])
    demo("f(x) = x + x + 1", [(0, 1), (1, 3), (2, 5), (3, 7)])
