class Node:
    """Parse-tree node used by the recursive-descent parser."""

    def __init__(
        self,
        name,
        children=None,
        is_terminal=False,
        token_kind=None,
        token_value=None,
        line=None,
        col=None,
    ):
        self.name = name
        self.children = children or []
        self.is_terminal = is_terminal
        self.token_kind = token_kind
        self.token_value = token_value
        self.line = line
        self.col = col

    def first_terminal(self):
        """Return the first terminal token contained in this subtree."""
        if self.is_terminal:
            return self

        for child in self.children:
            token = child.first_terminal()
            if token is not None:
                return token

        return None

class SyntaxErrors(Exception):
    def __init__(self, errors):
        super().__init__(f"{len(errors)} syntax error(s)")
        self.errors = errors

class Parser:  #All the functions defined below are parts of Parser class.
    def __init__(self, tokens, show_left=False, show_right=False, show_tree=False, show_gui_tree=False):
        self.tokens, self.pos, self.errors = tokens, 0, []
        self.flags = {'left': show_left, 'right': show_right, 'tree': show_tree, 'gui': show_gui_tree}
        self.lbls = {'semicolon': "';'", 'left_parenthesis': "'('", 'right_parenthesis': "')'", 'left_brace': "'{'", 'right_brace': "'}'", 'assignment': "'='"}

#decorator to make a method behave like an attribute, so that we can access the current token as self.curr instead of self.curr().
    @property  
    def curr(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]

        if len(self.tokens) > 0:
            line = self.tokens[-1][2] #getting the line no. of the LAST token, as list[-1] gives the last index.
            col = self.tokens[-1][3] + len(str(self.tokens[-1][1])) #doing the same for column.
                                         #finding the length of the value of last token.
        else:      #if no tokens are present, we assume line 1,column 1.                    
            line = 1
            col = 1
# note: (kind, value, line, col) this is the structure of a token. 
        return (None, None, line, col)

    @property
    def prev(self):  #returns the prevous token.
        return self.tokens[self.pos - 1] if self.pos > 0 else (None, None, 1, 1)

    def token_desc(self, k, v): return f"{k} {v!r}" if k else 'EOF' # where k is kind and v is value.

    #gets current token and raises an error.
    def error_here(self, exp=None, msg=None, line=None, col=None): #initialization to "none" assuming base case is no error.
        k, v, l, c = self.curr
        msg = msg or f"syntax error: expected {self.lbls.get(exp, exp)}, got {self.token_desc(k, v)}"
        err = SyntaxError(f"{msg} at line {line or l}, column {col or c}")
        err.line, err.col, err.message_only = line or l, col or c, msg
        raise err

    # after the first syntax error, we skip the tokens until we find a better restart point.
    def synchronize(self, stop_kind=None):
        while self.curr[0]:
            k, v, l, _ = self.curr
            pk, _, pl, _ = self.prev
            if k == stop_kind or (k == 'identifier' and (l > pl or pk in ['semicolon', 'left_brace', 'right_brace'])): return True
            self.pos += 1
            if k in ['semicolon', 'left_brace'] or (k == 'keyword' and v in ['int', 'float', 'if', 'while', 'for', 'print']): return True
        return False

    # this function consumes the current token if it matches the expected kind.
    def eat(self, exp):
        k, v, line, col = self.curr 
        if k == exp: #if the current token's kind matches expected, we increment position.
            self.pos += 1
            return Node(
                v,
                is_terminal=True,
                token_kind=k,
                token_value=v,
                line=line,
                col=col,
            )
        if exp == 'semicolon' and self.pos > 0:
            self.error_here(exp,line=self.prev[2], col=self.prev[3] + len(str(self.prev[1])))
        self.error_here(exp)

    def parse_statement_list(self, stop_kind=None):
        nodes = []
        while self.curr[0] and self.curr[0] != stop_kind:
            try: nodes.append(self.parse_statement())
            except SyntaxError as e:
                self.errors.append(e)
                if not self.synchronize(stop_kind): break #calls sync function and breaks if it reaches EOF.
        if stop_kind == 'right_brace' and not self.curr[0]: #note: self.curr[0] is the kind.
            self.errors.append(self.error_here(msg="syntax error: expected '}' to close block"))
        return nodes

    def _binop(self, name, func, tk, ops=None):
        n = Node(name, [func()])
        while self.curr[0] == tk and (not ops or self.curr[1] in ops):
            n.children.extend([self.eat(tk), func()])
        return n

    #Parse addition and subtraction.
    def parse_expr(self): return self._binop("Expression", self.parse_term, 'arithmetic_operator', ['+', '-'])
    #Parse mul, div, mod.
    def parse_term(self): return self._binop("Term", self.parse_factor, 'arithmetic_operator', ['*', '/', '%'])
    #Parse logical OR.
    def parse_bool_expr(self): return self._binop("BooleanExpression", self.parse_bool_term, 'boolean_operator', ['||'])
    #Parse logical AND.
    def parse_bool_term(self): return self._binop("BooleanTerm", self.parse_bool_factor, 'boolean_operator', ['&&'])

    def parse_factor(self):
        k, v = self.curr[:2]
        if k in ['integer_constant', 'float_constant', 'identifier']: return Node("Factor", [self.eat(k)])
        if k == 'left_parenthesis': return Node("Factor", [self.eat('left_parenthesis'), self.parse_expr(), self.eat('right_parenthesis')])
        self.error_here(msg=f"syntax error: expected factor, got {self.token_desc(k, v)}")

    def parse_assignment_core(self):
        return Node("Assignment", [self.eat('identifier'), self.eat('assignment'), self.parse_expr()])

    def parse_for_update(self):
        identifier = self.eat('identifier')
        if self.curr[0] == 'increment_operator':
            increment = self.eat('increment_operator')
            expr = Node(
                "Expression",
                [
                    Node("Term", [Node("Factor", [Node(identifier.token_value, is_terminal=True, token_kind=identifier.token_kind, token_value=identifier.token_value, line=identifier.line, col=identifier.col)])]),
                    Node("+", is_terminal=True, token_kind='arithmetic_operator', token_value='+', line=increment.line, col=increment.col),
                    Node("Term", [Node("Factor", [Node("1", is_terminal=True, token_kind='integer_constant', token_value='1', line=increment.line, col=increment.col)])]),
                ],
            )
            return Node("Assignment", [identifier, Node("=", is_terminal=True, token_kind='assignment', token_value='=', line=identifier.line, col=identifier.col), expr])

        return Node("Assignment", [identifier, self.eat('assignment'), self.parse_expr()])

    def parse_for(self):
        header = [self.eat('keyword'), self.eat('left_parenthesis')]
        init = self.parse_assignment_core()
        header.append(self.eat('semicolon'))
        condition = self.parse_bool_expr()
        header.append(self.eat('semicolon'))
        update = self.parse_for_update()
        header.append(self.eat('right_parenthesis'))
        body = self.parse_statement()

        while_body_children = []
        if body.name == "Statement" and body.children[0].name == "Block":
            while_body_children.extend(body.children[0].children)
        else:
            while_body_children.append(body)
        while_body_children.append(Node("Statement", [update]))

        while_node = Node(
            "WhileStatement",
            [
                Node("while", is_terminal=True, token_kind='keyword', token_value='while'),
                Node("(", is_terminal=True, token_kind='left_parenthesis', token_value='('),
                condition,
                Node(")", is_terminal=True, token_kind='right_parenthesis', token_value=')'),
                Node("Statement", [Node("Block", [Node("{", is_terminal=True, token_kind='left_brace', token_value='{')] + while_body_children + [Node("}", is_terminal=True, token_kind='right_brace', token_value='}')])]),
            ],
        )

        return Node("Statement", [Node("Block", [Node("{", is_terminal=True, token_kind='left_brace', token_value='{'), Node("Statement", [Node("Assignment", init.children + [Node(";", is_terminal=True, token_kind='semicolon', token_value=';')])]), Node("Statement", [while_node]), Node("}", is_terminal=True, token_kind='right_brace', token_value='}')])])

    def parse_bool_factor(self):
        v = self.curr[1]
        if v == '!': return Node("BooleanFactor", [self.eat('boolean_operator'), self.parse_bool_factor()])
        if v == '(':
            start = self.pos
            try:
                kids = [self.parse_expr()]
                if self.curr[0] == 'relational_operator':
                    kids.extend([self.eat('relational_operator'), self.parse_expr()])
                return Node("BooleanFactor", kids)
            except SyntaxError as expr_error:
                self.pos = start
                try:
                    return Node("BooleanFactor", [self.eat('left_parenthesis'), self.parse_bool_expr(), self.eat('right_parenthesis')])
                except SyntaxError:
                    self.pos = start
                    raise expr_error
        kids = [self.parse_expr()]
        if self.curr[0] == 'relational_operator': kids.extend([self.eat('relational_operator'), self.parse_expr()])
        return Node("BooleanFactor", kids)

    def parse_statement(self):
        k, v = self.curr[:2]
        #declaring a variable: int x; or float y;
        if k == 'keyword' and v in ['int', 'float']: return Node("Statement", [Node("Declaration", [self.eat('keyword'), self.eat('identifier'), self.eat('semicolon')])])
        #if statement with else part optional.
        if k == 'keyword' and v == 'if':
            kids = [self.eat('keyword'), self.eat('left_parenthesis'), self.parse_bool_expr(), self.eat('right_parenthesis'), self.parse_statement()]
            if self.curr[1] == 'else': kids.extend([self.eat('keyword'), self.parse_statement()])
            return Node("Statement", [Node("IfStatement", kids)])
        #while loop statement.
        if k == 'keyword' and v == 'while': return Node("Statement", [Node("WhileStatement", [self.eat('keyword'), self.eat('left_parenthesis'), self.parse_bool_expr(), self.eat('right_parenthesis'), self.parse_statement()])])
        if k == 'keyword' and v == 'for': return self.parse_for()
        #print statement.
        if k == 'keyword' and v == 'print': return Node("Statement", [Node("PrintStatement", [self.eat('keyword'), self.eat('left_parenthesis'), self.parse_expr(), self.eat('right_parenthesis'), self.eat('semicolon')])])
        #block { ... }
        if k == 'left_brace': return Node("Statement", [Node("Block", [self.eat('left_brace')] + self.parse_statement_list('right_brace') + ([self.eat('right_brace')] if self.curr[0] == 'right_brace' else []))])
        #assignment : x = 10;
        if k == 'identifier': return Node("Statement", [Node("Assignment", [self.eat('identifier'), self.eat('assignment'), self.parse_expr(), self.eat('semicolon')])])
        self.error_here(msg=f"syntax error: unexpected start of statement: {self.token_desc(k, v)}")

    
    '''Program
       StatementList
       Statement StatementList
       Declaration StatementList
       int id ; StatementList
    ...
    '''
    #for getting the leftmost and rightmost derivation steps like above.
    def get_derivation(self, root, mode="left"):
        steps, form = [], [root]
        steps.append(" ".join(n.name for n in form))
        while not all(n.is_terminal for n in form):
            idx = next(i for i in (range(len(form)) if mode == "left" else range(len(form)-1, -1, -1)) if not form[i].is_terminal)
            form = form[:idx] + form[idx].children + form[idx+1:]
            steps.append(" ".join(n.name for n in form))
        return steps

    def print_tree(self, node, level=0):
        if self.flags['tree']:
            print("  " * level + "|-- " + str(node.name))
            for c in node.children: self.print_tree(c, level + 1)

    def parse_program(self):
        root = Node("Program", self.parse_statement_list())
        if self.errors: raise SyntaxErrors(self.errors)
        print("Syntactic Validation Successful.")
        if self.flags['gui']:
            from pipeline.tree_view import draw_with_nltk; draw_with_nltk(root, hide_terminals=True)
        self.print_tree(root)
        for m in ['left', 'right']:
            if self.flags[m]:
                print(f"\n--- {m.capitalize()}most Derivation ---")
                for i, step in enumerate(self.get_derivation(root, m)): print(f" {'=>' if i else '  '} {step}")
        return root
