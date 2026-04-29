"""Intermediate Code Generation — Three-Address Code (Quadruples).

Each instruction is represented as a 4-tuple:
    (op, arg1, arg2, result)

Control-flow ops
----------------
  label            ""      ""      L<n>       -- define a label
  goto             ""      ""      L<n>       -- unconditional jump
  if_false_goto    tN      ""      L<n>       -- jump if tN is false/0

Data / computation ops
----------------------
  =                rhs     ""      lhs        -- simple copy / assignment
  +  -  *  /  %   left    right   tN         -- arithmetic into temp
  <  >  <=  >=
  ==  !=           left    right   tN         -- relational into temp (bool)
  &&  ||           left    right   tN         -- logical binary into temp
  !                arg     ""      tN         -- logical NOT into temp
  print            arg     ""      ""         -- output statement
"""


class TACGenerator:
    """Walk the parse tree produced by Parser and emit Quadruples."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __init__(self):
        self._quads: list[tuple[str, str, str, str]] = []
        self._temp_count = 0
        self._label_count = 0

    def generate(self, root) -> list[tuple[str, str, str, str]]:
        """Generate TAC for an entire program node and return the quad list."""
        self._quads = []
        self._temp_count = 0
        self._label_count = 0
        self._gen_program(root)
        return self._quads

    # ------------------------------------------------------------------
    # Counter helpers
    # ------------------------------------------------------------------

    def _new_temp(self) -> str:
        """Return the next unique temporary variable name."""
        name = f"t{self._temp_count}"
        self._temp_count += 1
        return name

    def _new_label(self) -> str:
        """Return the next unique label name."""
        name = f"L{self._label_count}"
        self._label_count += 1
        return name

    # ------------------------------------------------------------------
    # Quad emission
    # ------------------------------------------------------------------

    def _emit(self, op: str, arg1: str = "", arg2: str = "", result: str = ""):
        """Append one quad to the instruction list."""
        self._quads.append((op, arg1, arg2, result))

    # ------------------------------------------------------------------
    # Top-level dispatch
    # ------------------------------------------------------------------

    def _gen_program(self, node):
        for child in node.children:
            if child.name == "Statement":
                self._gen_statement(child)

    def _gen_statement(self, node):
        inner = node.children[0]
        dispatch = {
            "Declaration":    self._gen_declaration,
            "Assignment":     self._gen_assignment,
            "PrintStatement": self._gen_print,
            "IfStatement":    self._gen_if,
            "WhileStatement": self._gen_while,
            "Block":          self._gen_block,
        }
        handler = dispatch.get(inner.name)
        if handler:
            handler(inner)

    def _gen_block(self, node):
        for child in node.children:
            if child.name == "Statement":
                self._gen_statement(child)

    # ------------------------------------------------------------------
    # Declarations — no TAC emitted (handled by symbol table)
    # ------------------------------------------------------------------

    def _gen_declaration(self, node):
        # Declarations are purely a semantic concern; no TAC is needed.
        pass

    # ------------------------------------------------------------------
    # Assignment:  x = <expr> ;
    #   children: [identifier, '=', Expression, ';']
    # ------------------------------------------------------------------

    def _gen_assignment(self, node):
        lhs = node.children[0].token_value          # variable name
        rhs = self._gen_expr(node.children[2])      # evaluates expression
        self._emit("=", rhs, "", lhs)

    # ------------------------------------------------------------------
    # Print:  print ( <expr> ) ;
    #   children: ['print', '(', Expression, ')', ';']
    # ------------------------------------------------------------------

    def _gen_print(self, node):
        arg = self._gen_expr(node.children[2])
        self._emit("print", arg, "", "")

    # ------------------------------------------------------------------
    # If–else:
    #   children: ['if', '(', BoolExpr, ')', Statement, ...]
    #   optional: [..., 'else', Statement]
    # ------------------------------------------------------------------

    def _gen_if(self, node):
        cond = self._gen_bool_expr(node.children[2])

        has_else = len(node.children) > 5          # 'else' keyword is index 5

        l_false = self._new_label()
        l_end   = self._new_label() if has_else else l_false

        # if condition is false, jump past the true branch
        self._emit("if_false_goto", cond, "", l_false)

        # --- true branch ---
        self._gen_statement(node.children[4])

        if has_else:
            self._emit("goto", "", "", l_end)
            self._emit("label", "", "", l_false)
            # --- false branch ---
            self._gen_statement(node.children[6])

        self._emit("label", "", "", l_end)

    # ------------------------------------------------------------------
    # While:
    #   children: ['while', '(', BoolExpr, ')', Statement]
    # ------------------------------------------------------------------

    def _gen_while(self, node):
        l_start = self._new_label()
        l_end   = self._new_label()

        self._emit("label", "", "", l_start)

        cond = self._gen_bool_expr(node.children[2])
        self._emit("if_false_goto", cond, "", l_end)

        # --- loop body ---
        self._gen_statement(node.children[4])

        self._emit("goto", "", "", l_start)
        self._emit("label", "", "", l_end)

    # ------------------------------------------------------------------
    # Arithmetic expressions
    # ------------------------------------------------------------------

    def _gen_expr(self, node) -> str:
        """Generate TAC for an Expression node; return the result place."""
        # Expression children: Term (op Term)*
        result = self._gen_term(node.children[0])
        idx = 1
        while idx < len(node.children):
            op     = node.children[idx].token_value        # '+' or '-'
            right  = self._gen_term(node.children[idx + 1])
            tmp    = self._new_temp()
            self._emit(op, result, right, tmp)
            result = tmp
            idx   += 2
        return result

    def _gen_term(self, node) -> str:
        """Generate TAC for a Term node; return the result place."""
        # Term children: Factor (op Factor)*
        result = self._gen_factor(node.children[0])
        idx = 1
        while idx < len(node.children):
            op     = node.children[idx].token_value        # '*', '/', '%'
            right  = self._gen_factor(node.children[idx + 1])
            tmp    = self._new_temp()
            self._emit(op, result, right, tmp)
            result = tmp
            idx   += 2
        return result

    def _gen_factor(self, node) -> str:
        """Generate TAC for a Factor node; return the result place (no quad for atoms)."""
        child = node.children[0]

        # Parenthesised expression: '(' Expression ')'
        if (
            child.is_terminal
            and child.token_kind == "left_parenthesis"
            and len(node.children) == 3
        ):
            return self._gen_expr(node.children[1])

        # Atom: integer_constant, float_constant, identifier
        if child.is_terminal:
            return child.token_value

        # Fallback — should not happen in a well-formed AST
        return ""

    # ------------------------------------------------------------------
    # Boolean expressions
    # ------------------------------------------------------------------

    def _gen_bool_expr(self, node) -> str:
        """Generate TAC for a BooleanExpression node; return result place."""
        # BooleanExpression children: BoolTerm (|| BoolTerm)*
        result = self._gen_bool_term(node.children[0])
        idx = 1
        while idx < len(node.children):
            op    = node.children[idx].token_value          # '||'
            right = self._gen_bool_term(node.children[idx + 1])
            tmp   = self._new_temp()
            self._emit(op, result, right, tmp)
            result = tmp
            idx   += 2
        return result

    def _gen_bool_term(self, node) -> str:
        """Generate TAC for a BooleanTerm node; return result place."""
        # BooleanTerm children: BoolFactor (&& BoolFactor)*
        result = self._gen_bool_factor(node.children[0])
        idx = 1
        while idx < len(node.children):
            op    = node.children[idx].token_value          # '&&'
            right = self._gen_bool_factor(node.children[idx + 1])
            tmp   = self._new_temp()
            self._emit(op, result, right, tmp)
            result = tmp
            idx   += 2
        return result

    def _gen_bool_factor(self, node) -> str:
        """Generate TAC for a BooleanFactor node; return result place."""
        children = node.children

        # Case 1:  ! BoolFactor
        if (
            len(children) == 2
            and children[0].is_terminal
            and children[0].token_value == "!"
        ):
            operand = self._gen_bool_factor(children[1])
            tmp = self._new_temp()
            self._emit("!", operand, "", tmp)
            return tmp

        # Case 2:  '(' BooleanExpression ')'
        if (
            len(children) == 3
            and children[0].is_terminal
            and children[0].token_kind == "left_parenthesis"
            and children[1].name == "BooleanExpression"
        ):
            return self._gen_bool_expr(children[1])

        # Case 3:  Expression relop Expression
        if (
            len(children) == 3
            and children[1].is_terminal
            and children[1].token_kind == "relational_operator"
        ):
            left  = self._gen_expr(children[0])
            right = self._gen_expr(children[2])
            tmp   = self._new_temp()
            self._emit(children[1].token_value, left, right, tmp)
            return tmp

        # Case 4:  single Expression (used as boolean value)
        if len(children) == 1 and children[0].name == "Expression":
            return self._gen_expr(children[0])

        # Fallback
        return ""

    # ------------------------------------------------------------------
    # Pretty-printing helpers (called externally by test.py)
    # ------------------------------------------------------------------

    @staticmethod
    def format_quads(quads: list[tuple[str, str, str, str]]) -> str:
        """Return a human-readable table of quadruples."""
        col_w = [5, 16, 12, 12, 12]
        header_fields = ["#", "op", "arg1", "arg2", "result"]
        sep = "  " + "  ".join("-" * w for w in col_w)

        def row(fields):
            return "  " + "  ".join(str(f).ljust(w) for f, w in zip(fields, col_w))

        lines = [row(header_fields), sep]
        for i, (op, a1, a2, res) in enumerate(quads):
            lines.append(row([i, op, a1, a2, res]))
        return "\n".join(lines)

    @staticmethod
    def format_readable(quads: list[tuple[str, str, str, str]]) -> str:
        """Return plain human-readable TAC instructions (like a textbook)."""
        lines = []
        for i, (op, a1, a2, res) in enumerate(quads):
            if op == "label":
                lines.append(f"  {res}:")
            elif op == "goto":
                lines.append(f"  ({i:>2})  goto {res}")
            elif op == "if_false_goto":
                lines.append(f"  ({i:>2})  if {a1} == false goto {res}")
            elif op == "=":
                lines.append(f"  ({i:>2})  {res} = {a1}")
            elif op == "print":
                lines.append(f"  ({i:>2})  print {a1}")
            elif op == "!":
                lines.append(f"  ({i:>2})  {res} = !{a1}")
            else:
                # binary op: arithmetic, relational, boolean
                lines.append(f"  ({i:>2})  {res} = {a1} {op} {a2}")
        return "\n".join(lines)