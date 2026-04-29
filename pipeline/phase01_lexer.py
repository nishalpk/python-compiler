## GROUP: TARUN, NISHAL 2023A7PS0209U, CHIRU, CALEB

# Question 1: Lexical Specification and Tokenization (5 Marks)
# Date of Evaluation: 02/03/2026 - 05/03/2026
# Using the given language specification (int, float, control constructs, operators, etc.), formally 
# define the lexical structure of the language.
# You are required to:
# • Identify and classify all token categories relevant to the prescribed constructs.
# • Specify the regular expressions corresponding to each token class.
# • Implement a lexical analyzer that reads a source program and generates a token stream.
# • Demonstrate the token stream generated for the prescribed evaluation program.
# • Clearly report lexical errors, if any.
# Your lexical analyzer must correctly tokenize the entire evaluation program provided.

import re
# Lexer error class to handle unexpected characters. 
class LexerError(RuntimeError):
    def __init__(self, message, line, col):
        super().__init__(f"{message} at line {line}, column {col}")
        self.line = line
        self.col = col
        self.message_only = message

class Lexer:
    rules = [
    ('keyword',           r'\b(int|float|if|else|while|for|print)\b'),
    ('increment_operator', r'\+\+'),
    ('float_constant',    r'\d+\.\d+'),
    ('integer_constant',  r'\d+'),
    ('identifier',        r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('relational_operator', r'(<=|>=|==|!=|<|>)'),
    ('boolean_operator',  r'(&&|\|\||!)'),
    ('arithmetic_operator', r'(\+|-|\*|/|%)'),
    ('assignment',        r'='),
    ('semicolon',         r';'),
    ('left_parenthesis',  r'\('),
    ('right_parenthesis', r'\)'),
    ('left_brace',        r'\{'),
    ('right_brace',       r'\}'),
    ('skip',              r'[ \t\n]+'),     
    ('mismatch',          r'.'),                
    ]

    re_rules = '|'.join('(?P<%s>%s)' % pair for pair in rules)

    def __init__(self):
        pass

    def tokenize(self, code):
        tokens = []
        line = 1
        line_start = 0
        for mo in re.finditer(self.re_rules, code):
            kind = mo.lastgroup
            value = mo.group()
            col = mo.start() - line_start + 1  #tracking column number.
            # print(f"Matched {kind}: '{value}'")  
            if kind == 'skip':
                newline_count = value.count('\n')
                if newline_count:
                    line += newline_count  #tracking line number.
                    line_start = mo.start() + value.rfind('\n') + 1
                continue
            elif kind == 'mismatch':
                raise LexerError(f"Unexpected character '{value}'", line, col)
            else:
                tokens.append((kind, value, line, col)) # Lexer returns 4 things but we are hiding line,column while printing using _,_ in test.py.
        return tokens
