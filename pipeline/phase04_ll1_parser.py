## GROUP: TARUN, NISHAL 2023A7PS0209U, CHIRU, CALEB

# ============================================================
# phase04_ll1_parser.py - Table-driven LL(1) Predictive Parser
# Uses the grammar, FIRST, and FOLLOW sets from phase02_grammar.py
# ============================================================

from pipeline.phase02_grammar import (
    GRAMMAR, START_SYMBOL, EPSILON, TERMINALS,
    is_terminal, is_nonterminal,
    compute_first_sets, compute_follow_sets,
    first_of_string, tokens_to_terminals,
    print_first_sets, print_follow_sets,
)


class LL1Parser:
    """
    Table-driven LL(1) predictive parser.
    Builds a parsing table from FIRST/FOLLOW sets, then simulates
    top-down parsing with an explicit stack.
    """

    def __init__(self):
        self.first = compute_first_sets()
        self.follow = compute_follow_sets(self.first)
        self.table = {}   # table[(NonTerminal, terminal)] = production RHS
        self.conflicts = []
        self._build_table()

    # ---- Build the LL(1) parsing table ----
    def _build_table(self):
        for nt, prods in GRAMMAR.items():
            for rhs in prods:
                first_rhs = first_of_string(rhs, self.first)
                # For each terminal a in FIRST(rhs), add table entry
                for a in first_rhs:
                    if a != EPSILON:
                        self._add_table_entry((nt, a), rhs)
                # If eps in FIRST(rhs), add entry for each b in FOLLOW(nt)
                if EPSILON in first_rhs:
                    for b in self.follow[nt]:
                        self._add_table_entry((nt, b), rhs)

    def _add_table_entry(self, key, rhs):
        existing = self.table.get(key)
        if existing is None or existing == rhs:
            self.table[key] = rhs
            return

        chosen = self._resolve_conflict(existing, rhs)
        self.conflicts.append((key, existing, rhs, chosen))
        self.table[key] = chosen

    def _resolve_conflict(self, existing, candidate):
        if existing == [EPSILON] and candidate != [EPSILON]:
            return candidate
        if candidate == [EPSILON] and existing != [EPSILON]:
            return existing
        return existing

    # ---- Pretty-print the parsing table ----
    def print_table(self):
        nonterminals = list(GRAMMAR.keys())

        print("\n" + "=" * 50)
        print("  LL(1) Parsing Table")
        print("=" * 50)
        print("  Non-empty table entries are shown.")

        for nt in nonterminals:
            entries = []
            for t in sorted({terminal for nonterminal, terminal in self.table if nonterminal == nt}):
                entry = self.table.get((nt, t))
                if entry:
                    entries.append(f"{t}: {nt} -> {' '.join(entry)}")
            if entries:
                print(f"  {nt}: " + " | ".join(entries))

        if self.conflicts:
            print("\n  Conflict resolutions:")
            for (nt, terminal), old, new, chosen in self.conflicts:
                print(
                    f"  M[{nt}, {terminal}]: "
                    f"{nt} -> {' '.join(old)} vs {nt} -> {' '.join(new)}; "
                    f"using {nt} -> {' '.join(chosen)}"
                )

    # ---- Run LL(1) parsing with step-by-step trace ----
    def parse(self, tokens):
        input_syms = tokens_to_terminals(tokens)
        stack = ['$', START_SYMBOL]   # $ at bottom, start symbol on top
        ip = 0

        print("\n" + "=" * 50)
        print("  LL(1) Parsing Trace")
        print("=" * 50)
        sw, iw, aw = 90, 70, 50
        print(f"  {'Stack':<{sw}} {'Input':<{iw}} {'Action':<{aw}}")
        print(f"  {'-'*sw} {'-'*iw} {'-'*aw}")

        while True:
            top = stack[-1]
            curr_term, curr_val = input_syms[ip]

            stack_str = ' '.join(stack) + " <- [TOP]"
            input_str = ' '.join(v for _, v in input_syms[ip:])

            # Accept condition
            if top == '$' and curr_term == '$':
                print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ACCEPT':<{aw}}")
                print("\n>> Result: Parsing Successful")
                return True

            # Terminal on top of stack - try to match
            elif is_terminal(top) or top == '$':
                if top == curr_term:
                    action = f"Match '{curr_val}'"
                    print(f"  {stack_str:<{sw}} {input_str:<{iw}} {action:<{aw}}")
                    stack.pop()
                    ip += 1
                else:
                    print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ERROR':<{aw}}")
                    print(f"\n>> Parsing Error: expected '{top}', got '{curr_term}' ('{curr_val}')")
                    return False

            # Non-terminal on top - look up table
            elif is_nonterminal(top):
                key = (top, curr_term)
                if key in self.table:
                    prod = self.table[key]
                    prod_str = ' '.join(prod)
                    action = f"Expand {top} -> {prod_str}"
                    print(f"  {stack_str:<{sw}} {input_str:<{iw}} {action:<{aw}}")
                    stack.pop()
                    # Push RHS in reverse so leftmost symbol is on top
                    if prod != [EPSILON]:
                        for sym in reversed(prod):
                            stack.append(sym)
                else:
                    print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ERROR':<{aw}}")
                    expected = [t for (n, t) in self.table if n == top]
                    print(f"\n>> Parsing Error: unexpected '{curr_term}' ('{curr_val}') "
                          f"while expanding '{top}'")
                    if expected:
                        print(f"   Expected one of: {', '.join(sorted(set(expected)))}")
                    return False
            else:
                print(f"\n>> Parsing Error: unknown symbol '{top}' on stack")
                return False
