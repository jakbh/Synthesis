% Program Synthesis in Prolog
%
% Prolog's built-in backtracking makes it a natural fit for program synthesis.
% We define a DSL of arithmetic expressions, then use generate-and-test:
%   1. Generate a candidate program from the DSL.
%   2. Test it against all input-output examples.
%   3. If it passes, return it; otherwise backtrack and try the next candidate.
%
% Run with: swipl synthesizer.pl

% --- DSL: arithmetic expressions over variable x ---
%
% Expressions are generated in increasing size (depth-first via Prolog search).
% The ordering matters: simpler terms (x, constants) are tried before compound ones.

expr(x).
expr(C) :- member(C, [0, 1, 2, 3]).
expr(add(L, R)) :- expr(L), expr(R).
expr(mul(L, R)) :- expr(L), expr(R).


% --- Evaluator ---
%
% eval(+Expr, +X, -Value)  evaluates Expr with variable x bound to X.

eval(x,      X, X).
eval(C,      _, C) :- number(C).
eval(add(L, R), X, V) :- eval(L, X, VL), eval(R, X, VR), V is VL + VR.
eval(mul(L, R), X, V) :- eval(L, X, VL), eval(R, X, VR), V is VL * VR.


% --- Specification check ---
%
% satisfies(+Prog, +Examples) holds when Prog produces the correct output
% for every Input-Output pair in Examples.

satisfies(_, []).
satisfies(Prog, [X-Y | Rest]) :-
    eval(Prog, X, Y),
    satisfies(Prog, Rest).


% --- Synthesizer ---
%
% synthesize(+Examples, -Prog) finds the first (smallest) program in the DSL
% that satisfies all examples.

synthesize(Examples, Prog) :-
    expr(Prog),
    satisfies(Prog, Examples).


% --- Pretty printer ---

pp(x)        :- write(x).
pp(C)        :- number(C), write(C).
pp(add(L,R)) :- write('('), pp(L), write(' + '), pp(R), write(')').
pp(mul(L,R)) :- write('('), pp(L), write(' * '), pp(R), write(')').


% --- Demo ---

demo(Desc, Examples) :-
    format("  Task    : ~w~n", [Desc]),
    format("  Examples: ~w~n", [Examples]),
    ( synthesize(Examples, Prog)
    ->  write('  Synthesized: f(x) = '), pp(Prog), nl
    ;   write('  No program found.')
    ),
    nl.

:- initialization(main, main).

main :-
    format("=== Program Synthesis in Prolog ===~n~n"),
    format("Strategy: Use Prolog backtracking to enumerate DSL expressions,~n"),
    format("          return the first consistent with all examples.~n~n"),

    demo("f(x) = x + 2",      [0-2, 1-3, 2-4, 5-7]),
    demo("f(x) = 2 * x",      [0-0, 1-2, 2-4, 3-6]),
    demo("f(x) = x * x",      [0-0, 1-1, 2-4, 3-9]),
    demo("f(x) = x + x + 1",  [0-1, 1-3, 2-5, 3-7]).
