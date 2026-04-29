"""Semantic analysis and symbol-table tracing for the mini language."""

from pipeline.phase05_symbol_table import SymbolTable


BOOL_TYPE = "bool"
ERROR_TYPE = "<error>"


class SemanticError(RuntimeError):
    """Represent one semantic error with source location metadata."""

    def __init__(self, message, line, col):
        super().__init__(f"{message} at line {line}, column {col}")
        self.line = line
        self.col = col
        self.message_only = message


class SemanticAnalyzer:
    """Walk the parse tree, validate semantics, and track scope updates."""

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors = []
        self.trace_lines = []
        self.block_counter = 0

    def analyze(self, root):
        """Analyze the parse tree and return semantic errors plus trace text."""
        self.symbol_table = SymbolTable()
        self.errors = []
        self.trace_lines = []
        self.block_counter = 0

        self.symbol_table.enter_scope("global")
        self._record_trace("Enter scope 'global'")
        self._visit_program(root)

        return self.errors, self.trace_lines

    def _visit_program(self, node):
        """Analyze the top-level statement list inside the program node."""
        for child in node.children:
            if child.name == "Statement":
                self._visit_statement(child)

    def _visit_statement(self, node):
        """Dispatch semantic checks based on the wrapped statement kind."""
        statement = node.children[0]

        if statement.name == "Declaration":
            self._visit_declaration(statement)
        elif statement.name == "Assignment":
            self._visit_assignment(statement)
        elif statement.name == "PrintStatement":
            self._visit_print(statement)
        elif statement.name == "IfStatement":
            self._visit_if(statement)
        elif statement.name == "WhileStatement":
            self._visit_while(statement)
        elif statement.name == "Block":
            self._visit_block(statement)

    def _visit_block(self, node):
        """Create a nested scope for an explicit block and analyze its body."""
        scope_name = self._next_block_name()
        self.symbol_table.enter_scope(scope_name)
        self._record_trace(f"Enter scope '{scope_name}'")

        for child in node.children:
            if child.name == "Statement":
                self._visit_statement(child)

        exited_scope = self.symbol_table.exit_scope()
        self._record_trace(f"Exit scope '{exited_scope.name}'")

    def _visit_declaration(self, node):
        """Insert a declaration into the current scope and report duplicates."""
        type_node = node.children[0]
        identifier_node = node.children[1]
        identifier = identifier_node.token_value
        existing = self.symbol_table.lookup_current_scope(identifier)

        if existing is not None:
            self._add_error(
                f"multiple declarations of '{identifier}' in scope '{existing.scope_name}'",
                identifier_node,
            )
            return

        entry = self.symbol_table.insert(
            identifier,
            type_node.token_value,
            identifier_node.line,
            identifier_node.col,
        )
        self._record_trace(
            f"Insert '{entry.name}' as {entry.var_type} in scope '{entry.scope_name}' at offset {entry.offset}"
        )

    def _visit_assignment(self, node):
        """Validate assignments against declarations and inferred RHS types."""
        identifier_node = node.children[0]
        identifier = identifier_node.token_value
        entry = self.symbol_table.lookup(identifier)
        expr_type = self._analyze_expression(node.children[2])

        if entry is None:
            self._add_error(f"use of undeclared variable '{identifier}'", identifier_node)
            return

        if expr_type not in (ERROR_TYPE, entry.var_type):
            self._add_error(
                f"type mismatch in assignment to '{identifier}': expected {entry.var_type}, got {expr_type}",
                identifier_node,
            )

    def _visit_print(self, node):
        """Analyze the expression used in a print statement."""
        self._analyze_expression(node.children[2])

    def _visit_if(self, node):
        """Validate the if-condition and analyze its branches."""
        condition_type = self._analyze_bool_expression(node.children[2])
        self._validate_condition(node.children[2], condition_type)
        self._visit_statement(node.children[4])

        if len(node.children) > 5:
            self._visit_statement(node.children[6])

    def _visit_while(self, node):
        """Validate the while-condition and analyze its body."""
        condition_type = self._analyze_bool_expression(node.children[2])
        self._validate_condition(node.children[2], condition_type)
        self._visit_statement(node.children[4])

    def _validate_condition(self, condition_node, condition_type):
        """Reject conditions that do not evaluate to a boolean value."""
        if condition_type not in (BOOL_TYPE, ERROR_TYPE):
            self._add_error("invalid boolean condition", condition_node)

    def _analyze_bool_expression(self, node):
        """Infer the type of a boolean-expression subtree."""
        result_type = self._analyze_bool_term(node.children[0])
        index = 1

        while index < len(node.children):
            operator_node = node.children[index]
            rhs_type = self._analyze_bool_term(node.children[index + 1])
            result_type = self._resolve_boolean_operator(operator_node, result_type, rhs_type)
            index += 2

        return result_type

    def _analyze_bool_term(self, node):
        """Infer the type of a boolean-term subtree."""
        result_type = self._analyze_bool_factor(node.children[0])
        index = 1

        while index < len(node.children):
            operator_node = node.children[index]
            rhs_type = self._analyze_bool_factor(node.children[index + 1])
            result_type = self._resolve_boolean_operator(operator_node, result_type, rhs_type)
            index += 2

        return result_type

    def _analyze_bool_factor(self, node):
        """Infer the type of a boolean-factor subtree."""
        children = node.children

        if len(children) == 2 and children[0].is_terminal and children[0].token_value == "!":
            operand_type = self._analyze_bool_factor(children[1])
            if operand_type == ERROR_TYPE:
                return ERROR_TYPE
            if operand_type != BOOL_TYPE:
                self._add_error("operator '!' requires a boolean operand", children[0])
                return ERROR_TYPE
            return BOOL_TYPE

        if (
            len(children) == 3
            and children[0].is_terminal
            and children[0].token_kind == "left_parenthesis"
            and children[1].name == "BooleanExpression"
        ):
            return self._analyze_bool_expression(children[1])

        if len(children) == 3 and children[1].is_terminal and children[1].token_kind == "relational_operator":
            left_type = self._analyze_expression(children[0])
            right_type = self._analyze_expression(children[2])
            return self._resolve_relational_operator(children[1], left_type, right_type)

        if len(children) == 1 and children[0].name == "Expression":
            return self._analyze_expression(children[0])

        self._add_error("unable to analyze boolean factor", node)
        return ERROR_TYPE

    def _analyze_expression(self, node):
        """Infer the type of an arithmetic expression subtree."""
        result_type = self._analyze_term(node.children[0])
        index = 1

        while index < len(node.children):
            operator_node = node.children[index]
            rhs_type = self._analyze_term(node.children[index + 1])
            result_type = self._resolve_arithmetic_operator(operator_node, result_type, rhs_type)
            index += 2

        return result_type

    def _analyze_term(self, node):
        """Infer the type of a multiplicative term subtree."""
        result_type = self._analyze_factor(node.children[0])
        index = 1

        while index < len(node.children):
            operator_node = node.children[index]
            rhs_type = self._analyze_factor(node.children[index + 1])
            result_type = self._resolve_arithmetic_operator(operator_node, result_type, rhs_type)
            index += 2

        return result_type

    def _analyze_factor(self, node):
        """Infer the type of the factor represented by this subtree."""
        child = node.children[0]

        if child.is_terminal:
            if child.token_kind == "integer_constant":
                return "int"
            if child.token_kind == "float_constant":
                return "float"
            if child.token_kind == "identifier":
                entry = self.symbol_table.lookup(child.token_value)
                if entry is None:
                    self._add_error(f"use of undeclared variable '{child.token_value}'", child)
                    return ERROR_TYPE
                return entry.var_type

        if len(node.children) == 3 and node.children[0].is_terminal and node.children[0].token_kind == "left_parenthesis":
            return self._analyze_expression(node.children[1])

        self._add_error("unable to analyze factor", node)
        return ERROR_TYPE

    def _resolve_arithmetic_operator(self, operator_node, left_type, right_type):
        """Validate arithmetic operands and return the resulting type."""
        operator = operator_node.token_value

        if ERROR_TYPE in (left_type, right_type):
            return ERROR_TYPE

        if operator == "%":
            if left_type != "int" or right_type != "int":
                self._add_error("operator '%' requires int operands", operator_node)
                return ERROR_TYPE
            return "int"

        if not self._is_numeric(left_type) or not self._is_numeric(right_type):
            self._add_error(f"operator '{operator}' requires numeric operands", operator_node)
            return ERROR_TYPE

        if left_type != right_type:
            self._add_error(
                f"type mismatch in expression: {left_type} {operator} {right_type}",
                operator_node,
            )
            return ERROR_TYPE

        return left_type

    def _resolve_relational_operator(self, operator_node, left_type, right_type):
        """Validate relational operands and return the boolean result type."""
        operator = operator_node.token_value

        if ERROR_TYPE in (left_type, right_type):
            return ERROR_TYPE

        if not self._is_numeric(left_type) or not self._is_numeric(right_type):
            self._add_error(f"operator '{operator}' requires numeric operands", operator_node)
            return ERROR_TYPE

        if left_type != right_type:
            self._add_error(
                f"type mismatch in expression: {left_type} {operator} {right_type}",
                operator_node,
            )
            return ERROR_TYPE

        return BOOL_TYPE

    def _resolve_boolean_operator(self, operator_node, left_type, right_type):
        """Validate boolean operands and return the boolean result type."""
        if ERROR_TYPE in (left_type, right_type):
            return ERROR_TYPE

        if left_type != BOOL_TYPE or right_type != BOOL_TYPE:
            self._add_error(
                f"operator '{operator_node.token_value}' requires boolean operands",
                operator_node,
            )
            return ERROR_TYPE

        return BOOL_TYPE

    def _is_numeric(self, value_type):
        """Return whether the inferred type is numeric."""
        return value_type in {"int", "float"}

    def _next_block_name(self):
        """Generate a predictable nested block-scope name."""
        self.block_counter += 1
        return f"block_{self.block_counter}"

    def _add_error(self, message, node):
        """Create a semantic error anchored to the first token in a subtree."""
        token = node.first_terminal() if node is not None else None
        line = token.line if token and token.line is not None else 1
        col = token.col if token and token.col is not None else 1
        self.errors.append(SemanticError(message, line, col))

    def _record_trace(self, message):
        """Append one trace event together with a snapshot of active symbols."""
        self.trace_lines.append(message)
        self.trace_lines.extend(self._format_snapshot())
        self.trace_lines.append("")

    def _format_snapshot(self):
        """Render the active symbol table in a compact tabular format."""
        snapshot = sorted(
            self.symbol_table.snapshot_active_scopes(),
            key=lambda entry: (entry.scope_level, entry.offset, entry.name),
        )

        if not snapshot:
            return ["  Active symbols: <empty>"]

        lines = [
            "  Active symbols:",
            "    Name         Type   Scope      Level Offset",
            "    ------------ ------ ---------- ----- ------",
        ]

        for entry in snapshot:
            lines.append(
                f"    {entry.name:<12} {entry.var_type:<6} {entry.scope_name:<10} {entry.scope_level:<5} {entry.offset:<6}"
            )

        return lines
