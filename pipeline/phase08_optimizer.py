"""Basic optimization pass for Three-Address Code quadruples."""

from typing import TypeAlias


Quad: TypeAlias = tuple[str, str, str, str]

ARITHMETIC_OPERATORS: set[str] = {"+", "-", "*", "/", "%"}
RELATIONAL_OPERATORS: set[str] = {"<", ">", "<=", ">=", "==", "!="}
BOOLEAN_OPERATORS: set[str] = {"&&", "||"}


def optimize_quads(quads: list[Quad]) -> list[Quad]:
    """Return optimized quadruples without mutating the original TAC list."""
    folded: list[Quad] = []
    constants: dict[str, str] = {}

    for quad in quads:
        optimized_quad = optimize_quad(quad, constants)
        folded.append(optimized_quad)
        constants = update_constants(optimized_quad, constants)

    propagated = propagate_single_use_temporaries(folded)
    return remove_unused_temp_copies(propagated)


def propagate_single_use_temporaries(quads: list[Quad]) -> list[Quad]:
    """Write simple temp expressions directly into their final assignment target."""
    use_counts = count_operand_uses(quads)
    optimized: list[Quad] = []
    index = 0

    while index < len(quads):
        current_quad = quads[index]

        if index + 1 < len(quads) and can_merge_with_assignment(current_quad, quads[index + 1], use_counts):
            op, arg1, arg2, _ = current_quad
            _, _, _, final_result = quads[index + 1]
            optimized.append((op, arg1, arg2, final_result))
            index += 2
            continue

        optimized.append(current_quad)
        index += 1

    return optimized


def count_operand_uses(quads: list[Quad]) -> dict[str, int]:
    """Count how many times each TAC value is read as an operand."""
    counts: dict[str, int] = {}

    for op, arg1, arg2, _ in quads:
        if op != "label" and arg1:
            counts[arg1] = counts.get(arg1, 0) + 1
        if arg2:
            counts[arg2] = counts.get(arg2, 0) + 1

    return counts


def can_merge_with_assignment(current_quad: Quad, next_quad: Quad, use_counts: dict[str, int]) -> bool:
    """Return True when a temp-producing quad is immediately copied once."""
    op, _, _, result = current_quad
    next_op, next_arg1, _, next_result = next_quad

    if op not in ARITHMETIC_OPERATORS and op not in RELATIONAL_OPERATORS and op not in BOOLEAN_OPERATORS:
        return False
    if next_op != "=":
        return False
    if not is_temporary(result):
        return False
    if next_arg1 != result:
        return False
    if is_temporary(next_result):
        return False
    return use_counts.get(result, 0) == 1


def optimize_quad(quad: Quad, constants: dict[str, str]) -> Quad:
    """Optimize one quadruple using known constants and algebraic identities."""
    op, arg1, arg2, result = quad
    resolved_arg1 = resolve_constant(arg1, constants)
    resolved_arg2 = resolve_constant(arg2, constants)

    if op in ARITHMETIC_OPERATORS:
        folded = fold_numeric_operation(op, resolved_arg1, resolved_arg2)
        if folded is not None:
            return ("=", folded, "", result)

        simplified = simplify_arithmetic_operation(op, resolved_arg1, resolved_arg2)
        if simplified is not None:
            return ("=", simplified, "", result)

        return (op, resolved_arg1, resolved_arg2, result)

    if op == "=":
        return (op, resolved_arg1, "", result)

    if op == "print":
        return (op, resolved_arg1, "", result)

    return (op, resolved_arg1, resolved_arg2, result)


def update_constants(quad: Quad, constants: dict[str, str]) -> dict[str, str]:
    """Return the constant table after one optimized quadruple."""
    op, arg1, _, result = quad

    if op in {"label", "goto", "if_false_goto"}:
        return {}

    updated = constants.copy()

    if result:
        updated.pop(result, None)

    if op == "=" and result and is_numeric_literal(arg1):
        updated[result] = arg1

    return updated


def remove_unused_temp_copies(quads: list[Quad]) -> list[Quad]:
    """Drop temporary copy instructions that became unused after folding."""
    used_operands = collect_used_operands(quads)
    optimized: list[Quad] = []

    for quad in quads:
        op, _, _, result = quad
        if op == "=" and is_temporary(result) and result not in used_operands:
            continue
        optimized.append(quad)

    return optimized


def collect_used_operands(quads: list[Quad]) -> set[str]:
    """Collect every TAC operand read by an instruction."""
    used: set[str] = set()

    for op, arg1, arg2, _ in quads:
        if op != "label" and arg1:
            used.add(arg1)
        if arg2:
            used.add(arg2)

    return used


def is_temporary(value: str) -> bool:
    """Return whether a TAC value is a generated temporary name."""
    if not value.startswith("t"):
        return False
    return value[1:].isdigit()


def resolve_constant(value: str, constants: dict[str, str]) -> str:
    """Replace a known constant temporary or variable with its literal value."""
    return constants.get(value, value)


def fold_numeric_operation(op: str, left: str, right: str) -> str | None:
    """Evaluate an arithmetic operation when both operands are numeric literals."""
    if not is_numeric_literal(left) or not is_numeric_literal(right):
        return None

    if op == "/" and parse_numeric_literal(right) == 0:
        return None

    if op == "%" and parse_numeric_literal(right) == 0:
        return None

    if op == "+":
        return format_numeric_literal(parse_numeric_literal(left) + parse_numeric_literal(right))
    if op == "-":
        return format_numeric_literal(parse_numeric_literal(left) - parse_numeric_literal(right))
    if op == "*":
        return format_numeric_literal(parse_numeric_literal(left) * parse_numeric_literal(right))
    if op == "/":
        return format_numeric_literal(parse_numeric_literal(left) / parse_numeric_literal(right))
    if op == "%":
        return format_numeric_literal(parse_numeric_literal(left) % parse_numeric_literal(right))

    raise ValueError(f"unsupported arithmetic operator: {op}")


def simplify_arithmetic_operation(op: str, left: str, right: str) -> str | None:
    """Apply safe algebraic identities to one arithmetic operation."""
    if op == "+" and right == "0":
        return left
    if op == "+" and left == "0":
        return right
    if op == "-" and right == "0":
        return left
    if op == "*" and right == "1":
        return left
    if op == "*" and left == "1":
        return right
    if op == "*" and right == "0":
        return "0"
    if op == "*" and left == "0":
        return "0"
    if op == "/" and right == "1":
        return left
    return None


def is_numeric_literal(value: str) -> bool:
    """Return True when a TAC operand is an integer or float literal."""
    if not value:
        return False

    try:
        float(value)
    except ValueError:
        return False

    return True


def parse_numeric_literal(value: str) -> float:
    """Convert a numeric TAC literal to a Python number for folding."""
    return float(value)


def format_numeric_literal(value: float) -> str:
    """Format folded numbers using integer text when the result is integral."""
    if value.is_integer():
        return str(int(value))
    return str(value)
