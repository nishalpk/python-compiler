## GROUP: TARUN, NISHAL 2023A7PS0209U, CHIRU, CALEB

# ============================================================
# phase02_grammar.py - Formal grammar, FIRST sets, and FOLLOW sets
# Extracted from the recursive-descent parser in parser.py
# ============================================================

import re

# Terminal symbols mapped from lexer token kinds/values
TERMINALS = {
    'TYPE', 'ID', 'INT_CONST', 'FLOAT_CONST',
    'ADDOP', 'MULOP', 'RELOP', 'AND', 'OR', 'NOT', 'INC',
    'ASSIGN', 'SEMI', 'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    'IF', 'ELSE', 'WHILE', 'FOR', 'PRINT',
    '$',
}

EPSILON = 'eps'  # using ASCII to avoid encoding issues on Windows

# ----------------------------------------------------------------
# Grammar productions extracted from parser.py
# Left-recursion eliminated using standard tail-transform for LL(1).
# ----------------------------------------------------------------
GRAMMAR = {
    'Program':       [['StmtList']],
    'StmtList':      [['Stmt', 'StmtList'],
                      [EPSILON]],

    'Stmt':          [['Decl'],
                      ['IfStmt'],
                      ['WhileStmt'],
                      ['ForStmt'],
                      ['PrintStmt'],
                      ['Block'],
                      ['Assign']],

    'Decl':          [['TYPE', 'ID', 'SEMI']],
    'IfStmt':        [['IF', 'LPAREN', 'BoolExpr', 'RPAREN', 'Stmt', 'ElsePart']],
    'ElsePart':      [['ELSE', 'Stmt'],
                      [EPSILON]],
    'WhileStmt':     [['WHILE', 'LPAREN', 'BoolExpr', 'RPAREN', 'Stmt']],
    'ForStmt':       [['FOR', 'LPAREN', 'ForAssign', 'SEMI', 'BoolExpr', 'SEMI', 'ForUpdate', 'RPAREN', 'Stmt']],
    'PrintStmt':     [['PRINT', 'LPAREN', 'Expr', 'RPAREN', 'SEMI']],
    'Block':         [['LBRACE', 'StmtList', 'RBRACE']],
    'Assign':        [['ID', 'ASSIGN', 'Expr', 'SEMI']],
    'ForAssign':     [['ID', 'ASSIGN', 'Expr']],
    'ForUpdate':     [['ID', 'ASSIGN', 'Expr'],
                      ['ID', 'INC']],

    # Arithmetic expressions (left-recursion eliminated)
    'Expr':          [['Term', 'ExprTail']],
    'ExprTail':      [['ADDOP', 'Term', 'ExprTail'],
                      [EPSILON]],
    'Term':          [['Factor', 'TermTail']],
    'TermTail':      [['MULOP', 'Factor', 'TermTail'],
                      [EPSILON]],
    'Factor':        [['ID'], ['INT_CONST'], ['FLOAT_CONST'],
                      ['LPAREN', 'Expr', 'RPAREN']],

    # Boolean expressions (left-recursion eliminated)
    'BoolExpr':      [['BoolTerm', 'BoolETail']],
    'BoolETail':     [['OR', 'BoolTerm', 'BoolETail'],
                      [EPSILON]],
    'BoolTerm':      [['BoolFactor', 'BoolTTail']],
    'BoolTTail':     [['AND', 'BoolFactor', 'BoolTTail'],
                      [EPSILON]],
    'BoolFactor':    [['NOT', 'BoolFactor'],
                      ['Expr', 'RelPart']],
    'RelPart':       [['RELOP', 'Expr'],
                      [EPSILON]],
}

START_SYMBOL = 'Program'


def is_terminal(sym):
    return sym in TERMINALS or sym == EPSILON

def is_nonterminal(sym):
    return sym in GRAMMAR


# ----------------------------------------------------------------
# Map lexer tokens to grammar terminal names
# ----------------------------------------------------------------
def token_to_terminal(kind, value):
    """Convert a lexer token (kind, value) to our grammar terminal name."""
    if kind == 'keyword':
        return {'int': 'TYPE', 'float': 'TYPE',
                'if': 'IF', 'else': 'ELSE',
                'while': 'WHILE', 'for': 'FOR', 'print': 'PRINT'}.get(value, value)
    if kind == 'arithmetic_operator':
        return 'ADDOP' if value in ('+', '-') else 'MULOP'
    if kind == 'increment_operator':
        return 'INC'
    if kind == 'boolean_operator':
        return {'&&': 'AND', '||': 'OR', '!': 'NOT'}.get(value, value)
    return {
        'identifier': 'ID',
        'integer_constant': 'INT_CONST',
        'float_constant': 'FLOAT_CONST',
        'relational_operator': 'RELOP',
        'assignment': 'ASSIGN',
        'semicolon': 'SEMI',
        'left_parenthesis': 'LPAREN',
        'right_parenthesis': 'RPAREN',
        'left_brace': 'LBRACE',
        'right_brace': 'RBRACE',
    }.get(kind, kind)


def tokens_to_terminals(tokens):
    """Convert lexer token list to [(terminal, original_value), ..., ('$','$')]."""
    result = []
    for kind, value, line, col in tokens:
        result.append((token_to_terminal(kind, value), value))
    result.append(('$', '$'))
    return result


# ----------------------------------------------------------------
# FIRST set computation (fixed-point iteration)
# ----------------------------------------------------------------
def compute_first_sets():
    first = {nt: set() for nt in GRAMMAR}
    changed = True
    while changed:
        changed = False
        for nt, prods in GRAMMAR.items():
            for rhs in prods:
                for sym in rhs:
                    if sym == EPSILON:
                        if EPSILON not in first[nt]:
                            first[nt].add(EPSILON); changed = True
                        break
                    elif is_terminal(sym):
                        if sym not in first[nt]:
                            first[nt].add(sym); changed = True
                        break
                    else:
                        added = first[sym] - {EPSILON}
                        if not added.issubset(first[nt]):
                            first[nt] |= added; changed = True
                        if EPSILON not in first[sym]:
                            break
                else:
                    if EPSILON not in first[nt]:
                        first[nt].add(EPSILON); changed = True
    return first


# ----------------------------------------------------------------
# FOLLOW set computation (fixed-point iteration)
# ----------------------------------------------------------------
def compute_follow_sets(first):
    follow = {nt: set() for nt in GRAMMAR}
    follow[START_SYMBOL].add('$')
    changed = True
    while changed:
        changed = False
        for nt, prods in GRAMMAR.items():
            for rhs in prods:
                for i, sym in enumerate(rhs):
                    if not is_nonterminal(sym):
                        continue
                    rest = rhs[i + 1:]
                    first_rest = first_of_string(rest, first)
                    added = first_rest - {EPSILON}
                    if not added.issubset(follow[sym]):
                        follow[sym] |= added; changed = True
                    if EPSILON in first_rest or len(rest) == 0:
                        if not follow[nt].issubset(follow[sym]):
                            follow[sym] |= follow[nt]; changed = True
    return follow


def first_of_string(symbols, first):
    """FIRST set for a sequence of grammar symbols."""
    result = set()
    for sym in symbols:
        if sym == EPSILON:
            result.add(EPSILON); break
        elif is_terminal(sym):
            result.add(sym); break
        else:
            result |= (first[sym] - {EPSILON})
            if EPSILON not in first[sym]:
                break
    else:
        result.add(EPSILON)
    return result


# ----------------------------------------------------------------
# Pretty-print helpers
# ----------------------------------------------------------------
def print_first_sets(first):
    print("\n" + "=" * 50)
    print("  FIRST Sets")
    print("=" * 50)
    for nt in GRAMMAR:
        items = ', '.join(sorted(first[nt]))
        print(f"  FIRST({nt}) = {{ {items} }}")

def print_follow_sets(follow):
    print("\n" + "=" * 50)
    print("  FOLLOW Sets")
    print("=" * 50)
    for nt in GRAMMAR:
        items = ', '.join(sorted(follow[nt]))
        print(f"  FOLLOW({nt}) = {{ {items} }}")
