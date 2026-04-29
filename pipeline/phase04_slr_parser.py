## GROUP: TARUN, NISHAL 2023A7PS0209U, CHIRU, CALEB

# ============================================================
# phase04_slr_parser.py - Table-driven SLR parser
# Builds canonical LR(0) item sets, constructs SLR ACTION/GOTO
# tables using FOLLOW sets, and prints a shift/reduce stack trace.
# ============================================================

from collections import defaultdict, deque

from pipeline.phase02_grammar import (
    GRAMMAR,
    START_SYMBOL,
    EPSILON,
    TERMINALS,
    compute_first_sets,
    compute_follow_sets,
    is_nonterminal,
    tokens_to_terminals,
    print_first_sets,
    print_follow_sets,
)


class ShiftReduceParser:
    """
    SLR shift-reduce parser.

    The class name is kept as ShiftReduceParser because existing code already
    imports it under that name, but the implementation is now a formal SLR
    table parser instead of a heuristic suffix reducer.
    """

    def __init__(self):
        self.first = compute_first_sets()
        self.follow = compute_follow_sets(self.first)
        self.augmented_start = self._make_augmented_start()
        self.productions = self._build_numbered_productions()
        self.productions_by_lhs = self._group_productions()
        self.nonterminals = set(GRAMMAR) | {self.augmented_start}
        self.terminals = set(TERMINALS)
        self.grammar_symbols = self._collect_grammar_symbols()

        self.states = []
        self.transitions = {}
        self.action = {}
        self.goto_table = {}
        self.conflicts = []

        self._build_lr0_items()
        self._build_slr_tables()

    def _make_augmented_start(self):
        symbol = f"{START_SYMBOL}'"
        while symbol in GRAMMAR:
            symbol += "'"
        return symbol

    def _build_numbered_productions(self):
        productions = [(self.augmented_start, (START_SYMBOL,))]
        for lhs, alternatives in GRAMMAR.items():
            for rhs in alternatives:
                if rhs == [EPSILON]:
                    productions.append((lhs, ()))
                else:
                    productions.append((lhs, tuple(rhs)))
        return productions

    def _group_productions(self):
        grouped = defaultdict(list)
        for prod_no, (lhs, rhs) in enumerate(self.productions):
            grouped[lhs].append((prod_no, rhs))
        return grouped

    def _collect_grammar_symbols(self):
        symbols = set(GRAMMAR)
        for _, rhs in self.productions:
            symbols.update(rhs)
        symbols.discard(EPSILON)
        symbols.discard('$')
        return sorted(symbols)

    def _closure(self, items):
        closure_set = set(items)
        changed = True
        while changed:
            changed = False
            for prod_no, dot in list(closure_set):
                _, rhs = self.productions[prod_no]
                if dot >= len(rhs):
                    continue

                next_symbol = rhs[dot]
                if not is_nonterminal(next_symbol):
                    continue

                for next_prod_no, _ in self.productions_by_lhs[next_symbol]:
                    item = (next_prod_no, 0)
                    if item not in closure_set:
                        closure_set.add(item)
                        changed = True

        return frozenset(closure_set)

    def _goto(self, items, symbol):
        moved = []
        for prod_no, dot in items:
            _, rhs = self.productions[prod_no]
            if dot < len(rhs) and rhs[dot] == symbol:
                moved.append((prod_no, dot + 1))
        if not moved:
            return frozenset()
        return self._closure(moved)

    def _build_lr0_items(self):
        start_state = self._closure({(0, 0)})
        state_ids = {start_state: 0}
        self.states = [start_state]
        queue = deque([start_state])

        while queue:
            state = queue.popleft()
            state_no = state_ids[state]

            for symbol in self.grammar_symbols:
                next_state = self._goto(state, symbol)
                if not next_state:
                    continue

                if next_state not in state_ids:
                    state_ids[next_state] = len(self.states)
                    self.states.append(next_state)
                    queue.append(next_state)

                self.transitions[(state_no, symbol)] = state_ids[next_state]

    def _add_action(self, key, candidate):
        existing = self.action.get(key)
        if existing is None or existing == candidate:
            self.action[key] = candidate
            return

        chosen = self._resolve_conflict(existing, candidate)
        self.conflicts.append((key, existing, candidate, chosen))
        self.action[key] = chosen

    def _resolve_conflict(self, first_action, second_action):
        actions = {first_action[0], second_action[0]}
        if actions == {'shift', 'reduce'}:
            # Standard dangling-else resolution: shift so else binds to the
            # nearest unmatched if.
            return first_action if first_action[0] == 'shift' else second_action
        return first_action

    def _build_slr_tables(self):
        for state_no, state in enumerate(self.states):
            for prod_no, dot in state:
                lhs, rhs = self.productions[prod_no]

                if dot < len(rhs):
                    next_symbol = rhs[dot]
                    next_state = self.transitions.get((state_no, next_symbol))
                    if next_symbol in self.terminals and next_symbol != '$':
                        self._add_action((state_no, next_symbol), ('shift', next_state))
                    continue

                if lhs == self.augmented_start:
                    self._add_action((state_no, '$'), ('accept',))
                else:
                    for lookahead in self.follow[lhs]:
                        self._add_action((state_no, lookahead), ('reduce', prod_no))

            for nonterminal in sorted(GRAMMAR):
                next_state = self.transitions.get((state_no, nonterminal))
                if next_state is not None:
                    self.goto_table[(state_no, nonterminal)] = next_state

    def _format_production(self, prod_no):
        lhs, rhs = self.productions[prod_no]
        rhs_text = ' '.join(rhs) if rhs else EPSILON
        return f"{lhs} -> {rhs_text}"

    def _format_item(self, prod_no, dot):
        lhs, rhs = self.productions[prod_no]
        rhs_with_dot = list(rhs)
        rhs_with_dot.insert(dot, '.')
        rhs_text = ' '.join(rhs_with_dot) if rhs_with_dot else '.'
        return f"{lhs} -> {rhs_text}"

    def _format_action(self, action):
        kind = action[0]
        if kind == 'shift':
            return f"s{action[1]}"
        if kind == 'reduce':
            return f"r{action[1]}: {self._format_production(action[1])}"
        return 'acc'

    def _format_stack(self, state_stack, symbol_stack):
        pieces = [str(state_stack[0])]
        for symbol, state in zip(symbol_stack, state_stack[1:]):
            pieces.extend([symbol, str(state)])
        return ' '.join(pieces)

    def print_first_follow(self):
        print_first_sets(self.first)
        print_follow_sets(self.follow)

    def print_tables(self):
        print("\n" + "=" * 50)
        print("  LR(0) Item Sets")
        print("=" * 50)
        for state_no, state in enumerate(self.states):
            print(f"\n  I{state_no}:")
            for prod_no, dot in sorted(state):
                print(f"    {self._format_item(prod_no, dot)}")

        print("\n" + "=" * 50)
        print("  SLR ACTION / GOTO Table")
        print("=" * 50)
        print("  Non-empty table entries are shown.")
        for state_no in range(len(self.states)):
            actions = []
            gotos = []

            for terminal in sorted(self.terminals):
                entry = self.action.get((state_no, terminal))
                if entry:
                    actions.append(f"{terminal}:{self._format_action(entry)}")

            for nonterminal in sorted(GRAMMAR):
                entry = self.goto_table.get((state_no, nonterminal))
                if entry is not None:
                    gotos.append(f"{nonterminal}:{entry}")

            if actions or gotos:
                action_text = ', '.join(actions) if actions else '-'
                goto_text = ', '.join(gotos) if gotos else '-'
                print(f"  I{state_no:<3} ACTION[{action_text}]  GOTO[{goto_text}]")

        if self.conflicts:
            print("\n  Conflict resolutions:")
            for (state_no, terminal), old, new, chosen in self.conflicts:
                print(
                    f"  I{state_no} on {terminal}: "
                    f"{self._format_action(old)} vs {self._format_action(new)}; "
                    f"using {self._format_action(chosen)}"
                )

    def parse(self, tokens):
        input_syms = tokens_to_terminals(tokens)
        state_stack = [0]
        symbol_stack = []
        input_ptr = 0

        print("\n" + "=" * 50)
        print("  SLR Shift-Reduce Parsing Trace")
        print("=" * 50)
        sw, iw, aw = 90, 70, 60
        print(f"  {'Stack':<{sw}} {'Input':<{iw}} {'Action':<{aw}}")
        print(f"  {'-' * sw} {'-' * iw} {'-' * aw}")

        while True:
            state = state_stack[-1]
            curr_term, curr_val = input_syms[input_ptr]
            action = self.action.get((state, curr_term))

            stack_str = self._format_stack(state_stack, symbol_stack)
            input_str = ' '.join(value for _, value in input_syms[input_ptr:])

            if action is None:
                print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ERROR':<{aw}}")
                expected = sorted(
                    terminal for (s, terminal), _ in self.action.items()
                    if s == state
                )
                print(
                    f"\n>> Parsing Error: no ACTION entry for "
                    f"state I{state} and lookahead '{curr_term}' ('{curr_val}')"
                )
                if expected:
                    print(f"   Expected one of: {', '.join(expected)}")
                return False

            if action[0] == 'shift':
                next_state = action[1]
                action_text = f"SHIFT '{curr_val}', go to I{next_state}"
                print(f"  {stack_str:<{sw}} {input_str:<{iw}} {action_text:<{aw}}")
                symbol_stack.append(curr_term)
                state_stack.append(next_state)
                input_ptr += 1
                continue

            if action[0] == 'reduce':
                prod_no = action[1]
                lhs, rhs = self.productions[prod_no]
                pop_count = len(rhs)
                if pop_count:
                    del symbol_stack[-pop_count:]
                    del state_stack[-pop_count:]

                goto_state = self.goto_table.get((state_stack[-1], lhs))
                if goto_state is None:
                    print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ERROR':<{aw}}")
                    print(
                        f"\n>> Parsing Error: no GOTO entry for "
                        f"state I{state_stack[-1]} and nonterminal '{lhs}'"
                    )
                    return False

                symbol_stack.append(lhs)
                state_stack.append(goto_state)
                rhs_text = ' '.join(rhs) if rhs else EPSILON
                action_text = f"REDUCE r{prod_no}: {lhs} -> {rhs_text}; goto I{goto_state}"
                print(f"  {stack_str:<{sw}} {input_str:<{iw}} {action_text:<{aw}}")
                continue

            print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ACCEPT':<{aw}}")
            print("\n>> Result: Parsing Successful")
            return True
