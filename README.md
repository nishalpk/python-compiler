# Tarun Compiler

This project implements the assignment pipeline for a small `int`/`float` language:

- lexical analysis in `pipeline/phase01_lexer.py`
- grammar helpers in `pipeline/phase02_grammar.py`
- recursive-descent parsing in `pipeline/phase03_parser.py`
- table-driven LL(1) parsing in `pipeline/phase04_ll1_parser.py`
- table-driven SLR parsing in `pipeline/phase04_slr_parser.py`
- symbol-table construction and semantic analysis in `pipeline/phase05_symbol_table.py` and `pipeline/phase06_semantic_analyzer.py`

## Semantic Features

The semantic phase is built directly on the existing parse tree. It does not introduce a separate AST.

- Nested scopes are supported for explicit `{ ... }` blocks.
- Scope names are reported as `global`, `block_1`, `block_2`, and so on.
- Offsets are maintained per scope.
- Type sizes are fixed as:
  - `int = 4`
  - `float = 8`
- Shadowing is allowed across nested scopes.
- Multiple declarations are rejected inside the same scope.
- Identifier lookup searches from the innermost scope outward.

## Semantic Checks

The semantic analyzer reports:

- use of undeclared variables
- multiple declarations in the same scope
- type mismatches in assignments
- type mismatches in arithmetic and relational expressions
- invalid `%` usage on non-`int` operands
- invalid boolean operands for `&&`, `||`, and `!`
- invalid boolean conditions in `if` and `while`

Mixed `int`/`float` arithmetic is treated as a semantic error. There is no implicit type promotion.

## Run

Run the default evaluation program:

```bash
python3 pipeline/test.py
```

Run a specific example file:

```bash
python3 pipeline/test.py examples/undeclared_variable.tarun
python3 pipeline/test.py examples/duplicate_declaration.tarun
python3 pipeline/test.py examples/type_mismatch.tarun
python3 pipeline/test.py examples/invalid_boolean_condition.tarun
```

## Output Flow

For a valid input program, the driver prints:

1. token stream
2. recursive-descent parse tree and derivations
3. symbol-table update trace with active-scope snapshots
4. semantic validation success
5. LL(1) parser tables and trace
6. SLR parser tables and trace

If semantic errors are found, the driver still prints the symbol-table trace and semantic diagnostics, then stops before the LL(1) and SLR phases.

All console output is also mirrored into `output/output.txt`.

## Example Programs

- `input/code.tarun`: valid evaluation program with nested scopes, shadowing, `if`, `while`, `print`, and both `int` and `float`
- `examples/undeclared_variable.tarun`: undeclared identifier errors
- `examples/duplicate_declaration.tarun`: duplicate declarations in one scope
- `examples/type_mismatch.tarun`: assignment and expression type mismatches
- `examples/invalid_boolean_condition.tarun`: invalid boolean conditions and logical misuse

## Main Files

- `pipeline/phase01_lexer.py`: tokenization rules and lexical errors
- `pipeline/phase03_parser.py`: recursive-descent parser and parse-tree construction
- `pipeline/phase05_symbol_table.py`: scoped symbol-table implementation with offsets
- `pipeline/phase06_semantic_analyzer.py`: semantic checks and symbol-table trace generation
- `pipeline/phase07_tac.py`: TAC generation
- `pipeline/phase08_optimizer.py`: TAC optimization
- `pipeline/phase09_target_code.py`: pseudo assembly target-code generation
- `pipeline/test.py`: CLI driver for the full pipeline
