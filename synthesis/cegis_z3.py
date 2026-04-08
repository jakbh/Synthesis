"""
CEGIS: CounterExample-Guided Inductive Synthesis with Z3
=========================================================
Uses Z3 — an industrial-strength SMT (Satisfiability Modulo Theories) solver —
as an automated theorem prover in the verification step.

The CEGIS loop
--------------
  1. SYNTHESIZE  Find a candidate program consistent with all current examples.
  2. VERIFY      Ask Z3: "does candidate(x) == spec(x) for *every* integer x?"
                   - UNSAT  → no counterexample exists  → candidate is proven correct. Done.
                   - SAT    → Z3 returns a concrete counterexample cx.
                              Add (cx, spec(cx)) to examples and go to step 1.

Why this works
--------------
  Synthesis only needs to satisfy a *finite* set of examples — manageable.
  Verification checks the *infinite* integer domain — that's where Z3 shines.
  Counterexamples carry exactly the information needed to rule out the current
  (wrong) candidate class, so convergence is typically fast.

This is the core idea behind Sketch, Rosette, and many industrial synthesisers.

Requires: pip install z3-solver
"""

from itertools import product as iproduct
from z3 import Int, Solver, sat, unsat

# ---------------------------------------------------------------------------
# DSL — arithmetic expressions (single variable x)
# ---------------------------------------------------------------------------

class Var:
    def eval(self, env):    return env['x']
    def z3(self, x):        return x
    def __repr__(self):     return 'x'

class Const:
    def __init__(self, n):  self.n = n
    def eval(self, env):    return self.n
    def z3(self, x):        return self.n
    def __repr__(self):     return str(self.n)

class Add:
    def __init__(self, l, r): self.l, self.r = l, r
    def eval(self, env):    return self.l.eval(env) + self.r.eval(env)
    def z3(self, x):        return self.l.z3(x) + self.r.z3(x)
    def __repr__(self):     return f'({self.l} + {self.r})'

class Sub:
    def __init__(self, l, r): self.l, self.r = l, r
    def eval(self, env):    return self.l.eval(env) - self.r.eval(env)
    def z3(self, x):        return self.l.z3(x) - self.r.z3(x)
    def __repr__(self):     return f'({self.l} - {self.r})'

class Mul:
    def __init__(self, l, r): self.l, self.r = l, r
    def eval(self, env):    return self.l.eval(env) * self.r.eval(env)
    def z3(self, x):        return self.l.z3(x) * self.r.z3(x)
    def __repr__(self):     return f'({self.l} * {self.r})'

# ---------------------------------------------------------------------------
# Enumerative synthesiser (the "oracle" inside CEGIS)
# ---------------------------------------------------------------------------

def _enum(depth, constants):
    if depth == 0:
        yield Var()
        for c in constants:
            yield Const(c)
    else:
        yield from _enum(depth - 1, constants)
        for l, r in iproduct(_enum(depth - 1, constants), repeat=2):
            yield Add(l, r)
            yield Sub(l, r)
            yield Mul(l, r)

def find_candidate(examples, constants=(0, 1, 2, 3), max_depth=2):
    """Return the smallest program in the DSL consistent with all examples."""
    for depth in range(max_depth + 1):
        for prog in _enum(depth, constants):
            if all(prog.eval({'x': x}) == y for x, y in examples):
                return prog
    return None

# ---------------------------------------------------------------------------
# CEGIS loop
# ---------------------------------------------------------------------------

def cegis(spec_fn, spec_z3_fn, seed_inputs=(0, 1), max_iter=15):
    """
    Parameters
    ----------
    spec_fn      : int -> int   Concrete specification (used to label counterexamples).
    spec_z3_fn   : z3.Expr -> z3.Expr
                   Symbolic specification (used by Z3 during verification).
    seed_inputs  : initial inputs to bootstrap the example set.
    max_iter     : safety cap on the number of CEGIS iterations.

    Returns the synthesised program, or None if CEGIS did not converge.
    """
    x   = Int('x')
    examples = [(xi, spec_fn(xi)) for xi in seed_inputs]

    for iteration in range(1, max_iter + 1):
        print(f"  [{iteration}] examples = {examples}")

        # --- SYNTHESIZE --------------------------------------------------
        candidate = find_candidate(examples)
        if candidate is None:
            print("  Synthesiser exhausted the DSL — no candidate found.")
            return None
        print(f"      candidate : f(x) = {candidate}")

        # --- VERIFY ------------------------------------------------------
        # Ask Z3 whether there is ANY x for which candidate disagrees with spec.
        solver = Solver()
        solver.add(candidate.z3(x) != spec_z3_fn(x))
        result = solver.check()

        if result == unsat:
            # Proven: no x can distinguish candidate from spec.
            print(f"  Verified via Z3 (UNSAT — no counterexample exists).\n")
            return candidate

        elif result == sat:
            # Z3 produced a concrete counterexample.
            cx = solver.model()[x].as_long()
            cy = spec_fn(cx)
            print(f"      counterexample: x={cx}  spec={cy}  "
                  f"candidate={candidate.eval({'x': cx})}")
            examples.append((cx, cy))

        else:
            print("  Z3 returned UNKNOWN — stopping.")
            return None

    print("  Did not converge within iteration limit.")
    return None

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo(description, spec_fn, spec_z3_fn):
    print(f"Task: {description}")
    result = cegis(spec_fn, spec_z3_fn)
    if result:
        print(f"  Final answer: f(x) = {result}")
    print()

if __name__ == '__main__':
    print("=== CEGIS with Z3 (Automated Theorem Prover) ===\n")
    print("Each iteration: synthesise a candidate → verify with Z3 → refine.\n")
    print("=" * 56 + "\n")

    # f(x) = x + 2
    demo(
        "f(x) = x + 2",
        spec_fn    = lambda x: x + 2,
        spec_z3_fn = lambda x: x + 2,
    )

    # f(x) = 2 * x + 1
    demo(
        "f(x) = 2*x + 1",
        spec_fn    = lambda x: 2 * x + 1,
        spec_z3_fn = lambda x: 2 * x + 1,
    )

    # f(x) = x*x - x  (quadratic — tests depth-2 synthesis)
    demo(
        "f(x) = x*x - x",
        spec_fn    = lambda x: x * x - x,
        spec_z3_fn = lambda x: x * x - x,
    )

    # f(x) = (x + 1) * (x + 1)  — another quadratic
    demo(
        "f(x) = (x+1)*(x+1)",
        spec_fn    = lambda x: (x + 1) * (x + 1),
        spec_z3_fn = lambda x: (x + 1) * (x + 1),
    )
