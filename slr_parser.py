## GROUP: TARUN, NISHAL 2023A7PS0209U, CHIRU, CALEB

# ============================================================
# slr_parser.py - Naive Heuristic Shift-Reduce Parser
# Written by request to replace formal SLR(1) logic with
# relaxed heuristic reduction rules specifically tuned for naivety.
# ============================================================

from grammar import GRAMMAR, START_SYMBOL, EPSILON, tokens_to_terminals

class ShiftReduceParser:
    def __init__(self):
        # We discard the formal left-recursive/factored grammar here 
        # and instead use customized HEURISTIC rules for a naive parser,
        # ordered exactly by Longest-Match priority.
        self.productions = [
            # 5-length patterns
            ('WhileStmt', ['WHILE', 'LPAREN', 'Expr', 'RPAREN', 'Block']),
            
            # 4-length patterns
            ('Assign',    ['Expr', 'ASSIGN', 'Expr', 'SEMI']),
            
            # 3-length patterns
            ('Block',     ['LBRACE', 'StmtList', 'RBRACE']),
            ('Expr',      ['Expr', 'ADDOP', 'Expr']),
            ('Expr',      ['Expr', 'RELOP', 'Expr']),
            ('StmtList',  ['Stmt', 'StmtList']),
            
            # 1-length patterns (Cascading unit rules)
            ('Stmt',      ['Assign']),
            ('Stmt',      ['WhileStmt']),
            ('Stmt',      ['Block']),
            ('StmtList',  ['Stmt']),
            ('Expr',      ['Term']),
            ('Term',      ['Factor']),
            ('Factor',    ['ID']),
            ('Factor',    ['INT_CONST']),
            ('Factor',    ['FLOAT_CONST']),
            
            # Start Symbol resolution
            ('Program',   ['StmtList']),
        ]

    def print_first_follow(self):
        pass

    def print_tables(self):
        pass

    def parse(self, tokens):
        input_syms = tokens_to_terminals(tokens)
        input_ptr = 0
        stack = []
        
        sw, iw, aw = 90, 70, 50
        print("\n" + "=" * 50)
        print("  Shift-Reduce Parsing Trace (Heuristic Relaxed)")
        print("=" * 50)
        print(f"  {'Stack':<{sw}} {'Input':<{iw}} {'Action':<{aw}}")
        print(f"  {'-'*sw} {'-'*iw} {'-'*aw}")

        # The loop runs until input is exhausted and stack is successfully accepted,
        # or we get stuck (error).
        while True:
            # 1. ACCEPT CONDITION
            if stack == [START_SYMBOL] and input_syms[input_ptr][0] == '$':
                stack_str = ' '.join(stack)
                input_str = '$'
                print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ACCEPT':<{aw}}")
                print("\n>> Result: Parsing Successful")
                return True

            # 2. ITERATIVE LONGEST-MATCH REDUCTION
            # Keep reducing UNTIL no rule applies
            reduced_this_pass = True
            did_reduce = False
            
            while reduced_this_pass:
                reduced_this_pass = False
                for lhs, rhs in self.productions:
                    n = len(rhs)
                    if n > 0 and len(stack) >= n:
                        if stack[-n:] == rhs:
                            # To avoid prematurely wrapping intermediate statements into the final 'Program' 
                            # before the file ends, we restrict Program reductions to EOF.
                            if lhs == START_SYMBOL and input_syms[input_ptr][0] != '$':
                                continue
                                
                            action = f"REDUCE {lhs} -> {' '.join(rhs)}"
                            stack_str = ' '.join(stack)
                            input_str = ' '.join(v for _, v in input_syms[input_ptr:])
                            
                            # Print trace
                            print(f"  {stack_str:<{sw}} {input_str:<{iw}} {action:<{aw}}")
                            
                            # Apply reduction
                            stack = stack[:-n] + [lhs]
                            reduced_this_pass = True
                            did_reduce = True
                            break # restart with longest match
                            
            if did_reduce:
                # Loop around directly to check the acceptance condition again 
                # after we finish reducing.
                continue

            # 3. FAILURE CONDITION
            curr_term, curr_val = input_syms[input_ptr]
            if curr_term == '$':
                stack_str = ' '.join(stack)
                input_str = '$'
                print(f"  {stack_str:<{sw}} {input_str:<{iw}} {'>> ERROR (Stuck)':<{aw}}")
                print("\n>> Parsing Error: Could not shift or reduce any further.")
                return False
                
            # 4. SHIFT CONDITION
            action = f"SHIFT '{curr_val}'"
            stack_str = ' '.join(stack)
            input_str = ' '.join(v for _, v in input_syms[input_ptr:])
            
            # Print trace
            print(f"  {stack_str:<{sw}} {input_str:<{iw}} {action:<{aw}}")
            
            # Apply shift
            stack.append(curr_term)
            input_ptr += 1

