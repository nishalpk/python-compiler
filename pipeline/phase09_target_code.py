"""Pseudo assembly generation from optimized TAC quadruples."""

from typing import TypeAlias


Quad: TypeAlias = tuple[str, str, str, str]

INSTRUCTION_NAMES: dict[str, str] = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "/": "DIV",
    "%": "MOD",
    "<": "LT",
    ">": "GT",
    "<=": "LE",
    ">=": "GE",
    "==": "EQ",
    "!=": "NE",
    "&&": "AND",
    "||": "OR",
}


def generate_pseudo_assembly(quads: list[Quad]) -> str:
    """Convert optimized TAC quadruples into readable pseudo assembly."""
    lines: list[str] = []

    for quad in quads:
        lines.append(format_instruction(quad))

    return "\n".join(lines)


def format_instruction(quad: Quad) -> str:
    """Format one optimized TAC quadruple as one pseudo assembly instruction."""
    op, arg1, arg2, result = quad

    if op == "label":
        return f"{result}:"
    if op == "goto":
        return f"    JMP {result}"
    if op == "if_false_goto":
        return f"    JZ {arg1}, {result}"
    if op == "=":
        return f"    MOV {result}, {arg1}"
    if op == "print":
        return f"    PRINT {arg1}"
    if op == "!":
        return f"    NOT {result}, {arg1}"
    if op in INSTRUCTION_NAMES:
        instruction = INSTRUCTION_NAMES[op]
        return f"    {instruction} {result}, {arg1}, {arg2}"

    raise ValueError(f"unsupported TAC operation for target generation: {op}")
