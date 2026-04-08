// Advanced Program Synthesis in C++
// Technique: Enumerative Search with Observational Equivalence Pruning
//
// Key idea: instead of enumerating syntax trees naively, we group candidates
// by their *behaviour* (the vector of outputs on all example inputs).
// Two syntactically different programs with identical behaviour are redundant
// — we keep only one representative per equivalence class.
// This alone can reduce the search space by orders of magnitude.
//
// DSL
//   Terminals  : x, y, constants {-1, 0, 1, 2}
//   Binary ops : +, -, *
//   Conditional: ite(cond, then, else)  — if-then-else
//   Conditions : x < y, x == y, x > y
//
// With this DSL we can synthesise max(x,y), min(x,y), abs(x), etc.
//
// Compile: g++ -std=c++17 -O2 -o advanced_synthesis advanced_synthesis.cpp

#include <iostream>
#include <vector>
#include <memory>
#include <map>
#include <string>
#include <optional>

// ---------------------------------------------------------------------------
// Expression tree
// ---------------------------------------------------------------------------

using Env = std::pair<int, int>; // (x, y)

struct Expr {
    virtual int         eval(Env e) const = 0;
    virtual std::string str()       const = 0;
    virtual ~Expr() = default;
};
using ExprPtr = std::shared_ptr<Expr>;

struct Var : Expr {
    int idx;                                        // 0 = x, 1 = y
    explicit Var(int i) : idx(i) {}
    int         eval(Env e) const override { return idx == 0 ? e.first : e.second; }
    std::string str()       const override { return idx == 0 ? "x" : "y"; }
};

struct Const : Expr {
    int val;
    explicit Const(int v) : val(v) {}
    int         eval(Env)   const override { return val; }
    std::string str()       const override { return std::to_string(val); }
};

struct BinOp : Expr {
    char    op;
    ExprPtr l, r;
    BinOp(char op, ExprPtr l, ExprPtr r) : op(op), l(l), r(r) {}
    int eval(Env e) const override {
        int lv = l->eval(e), rv = r->eval(e);
        switch (op) {
            case '+': return lv + rv;
            case '-': return lv - rv;
            case '*': return lv * rv;
        }
        return 0;
    }
    std::string str() const override {
        return "(" + l->str() + " " + op + " " + r->str() + ")";
    }
};

// ---------------------------------------------------------------------------
// Conditions for if-then-else
// ---------------------------------------------------------------------------

struct Cond {
    std::string rel;
    bool eval(Env e) const {
        auto [x, y] = e;
        if (rel == "<")  return x < y;
        if (rel == "==") return x == y;
        if (rel == ">")  return x > y;
        return false;
    }
};

struct ITE : Expr {
    Cond    cond;
    ExprPtr then_e, else_e;
    ITE(Cond c, ExprPtr t, ExprPtr el) : cond(c), then_e(t), else_e(el) {}
    int eval(Env e) const override {
        return cond.eval(e) ? then_e->eval(e) : else_e->eval(e);
    }
    std::string str() const override {
        return "(if x " + cond.rel + " y then " +
               then_e->str() + " else " + else_e->str() + ")";
    }
};

// ---------------------------------------------------------------------------
// Synthesis
// ---------------------------------------------------------------------------

using Example    = std::pair<Env, int>;
using OutVector  = std::vector<int>;

OutVector outputs(ExprPtr prog, const std::vector<Example>& exs) {
    OutVector v;
    for (auto& [env, _] : exs)
        v.push_back(prog->eval(env));
    return v;
}

bool satisfies(ExprPtr prog, const std::vector<Example>& exs) {
    for (auto& [env, expected] : exs)
        if (prog->eval(env) != expected) return false;
    return true;
}

ExprPtr synthesize(const std::vector<Example>& exs) {
    // seen maps an output-vector → the first program producing that behaviour.
    // Any later program with the same output-vector is redundant and skipped.
    std::map<OutVector, bool> seen;

    auto consider = [&](ExprPtr p) -> std::optional<ExprPtr> {
        OutVector ov = outputs(p, exs);
        if (seen.count(ov)) return std::nullopt;   // OE pruning
        seen[ov] = true;
        if (satisfies(p, exs)) return p;
        return std::nullopt;
    };

    // --- Layer 0: terminals ---
    std::vector<ExprPtr> layer0;
    for (int i : {0, 1}) {
        auto e = std::make_shared<Var>(i);
        if (auto r = consider(e)) return *r;
        layer0.push_back(e);
    }
    for (int c : {-1, 0, 1, 2}) {
        auto e = std::make_shared<Const>(c);
        if (auto r = consider(e)) return *r;
        layer0.push_back(e);
    }

    // --- Layer 1: binary ops on layer-0 pairs ---
    std::vector<ExprPtr> layer1 = layer0;
    for (auto& l : layer0)
        for (auto& r : layer0)
            for (char op : {'+', '-', '*'}) {
                auto e = std::make_shared<BinOp>(op, l, r);
                if (auto res = consider(e)) return *res;
                layer1.push_back(e);
            }

    // --- Layer 2: ite(cond, layer1, layer1) ---
    for (auto& rel : std::vector<std::string>{"<", "==", ">"}) {
        Cond cond{rel};
        for (auto& t : layer1)
            for (auto& el : layer1) {
                auto e = std::make_shared<ITE>(cond, t, el);
                if (auto res = consider(e)) return *res;
            }
    }

    return nullptr;
}

// ---------------------------------------------------------------------------
// Demo
// ---------------------------------------------------------------------------

void demo(const std::string& desc, std::vector<Example> exs) {
    std::cout << "  Task    : " << desc << "\n";
    std::cout << "  Examples: ";
    for (auto& [env, out] : exs)
        std::cout << "f(" << env.first << "," << env.second << ")=" << out << "  ";
    std::cout << "\n";

    auto prog = synthesize(exs);
    if (prog)
        std::cout << "  Found   : f(x,y) = " << prog->str() << "\n";
    else
        std::cout << "  Not found within search depth.\n";
    std::cout << "\n";
}

int main() {
    std::cout << "=== Advanced Program Synthesis (C++) ===\n";
    std::cout << "Technique : Enumerative search + Observational Equivalence Pruning\n";
    std::cout << "DSL       : x, y, {-1,0,1,2}, +, -, *, if-then-else\n\n";

    demo("max(x, y)",          {{{3,1},3}, {{1,3},3}, {{5,5},5}, {{0,2},2}});
    demo("min(x, y)",          {{{3,1},1}, {{1,3},1}, {{5,5},5}, {{0,2},0}});
    demo("abs(x)  [y unused]", {{{-3,0},3}, {{3,0},3}, {{0,0},0}, {{-2,0},2}});
    demo("x + y",              {{{1,2},3}, {{3,4},7}, {{0,5},5}, {{-1,1},0}});
    demo("x - y",              {{{5,3},2}, {{3,5},-2}, {{4,4},0}, {{0,1},-1}});

    return 0;
}
