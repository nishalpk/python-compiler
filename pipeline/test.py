import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.phase01_lexer import Lexer, LexerError
from pipeline.phase02_grammar import print_first_sets, print_follow_sets
from pipeline.phase03_parser import Parser, SyntaxErrors
from pipeline.phase04_ll1_parser import LL1Parser
from pipeline.phase04_slr_parser import ShiftReduceParser
from pipeline.phase06_semantic_analyzer import SemanticAnalyzer
from pipeline.phase07_tac import TACGenerator
from pipeline.phase08_optimizer import optimize_quads
from pipeline.phase09_target_code import generate_pseudo_assembly


class Logger:
    """Mirror terminal output into output/output.txt for assignment demos."""

    def __init__(self):
        self.terminal = sys.stdout
        output_path = Path("output/output.txt")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = output_path.open("w", encoding="utf-8")

    def write(self, message):
        """Write one message to both stdout destinations."""
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        """Flush the terminal and log streams together."""
        self.terminal.flush()
        self.log.flush()


def configure_stdout_logger():
    """Install the tee-style stdout logger used by the project."""
    sys.stdout = Logger()


def print_error(filename, src, line, col, message):
    """Print an error together with the offending source line."""
    lines = src.splitlines()
    source_line = lines[line - 1] if 1 <= line <= len(lines) else ""
    print(f"{filename}:line->{line} col->{col}: error: {message}")
    print(source_line)
    print(" " * (max(col, 1) - 1) + "^")


def resolve_source_path(argv):
    """Resolve the source file path from the CLI arguments."""
    return argv[1] if len(argv) > 1 else "input/code.tarun"


def read_source(source_path):
    """Load the selected source program from disk."""
    return Path(source_path).read_text(encoding="utf-8")


def print_semantic_trace(trace_lines):
    """Print the symbol-table updates produced during semantic analysis."""
    print("\n\n\n Symbol Table and Semantic Analysis")
    print("=" * 60)
    for line in trace_lines:
        print(line)


def run_semantic_analysis(root, source_path, code):
    """Run semantic checks and return whether analysis succeeded."""
    analyzer = SemanticAnalyzer()
    semantic_errors, trace_lines = analyzer.analyze(root)
    print_semantic_trace(trace_lines)

    if semantic_errors:
        for error in semantic_errors:
            print_error(
                source_path,
                code,
                getattr(error, "line", 1),
                getattr(error, "col", 1),
                getattr(error, "message_only", str(error)),
            )
        return False

    print("Semantic Validation Successful.")
    return True

def run_tac_generation(root):
    """Generate TAC, optimize it, and print pseudo assembly target code."""
    print("\n\n\n Three-Address Code Generation")
    print("=" * 60)
    gen = TACGenerator()
    quads = gen.generate(root)

    print("\n--- Readable TAC ---")
    print(TACGenerator.format_readable(quads))

    print("\n--- Quadruples Table (op, arg1, arg2, result) ---")
    print(TACGenerator.format_quads(quads))

    print(f"\n  Total instructions: {len(quads)}")
    print("\nTAC Generation Successful.")

    optimized_quads = optimize_quads(quads)

    print("\n\n\n Question 5: Optimization and Target Code Generation")
    print("=" * 60)
    print("\n--- Optimization Technique ---")
    print("Constant folding, algebraic simplification, and single-use temporary propagation on generated TAC.")

    print("\n--- Optimized Readable TAC ---")
    print(TACGenerator.format_readable(optimized_quads))

    print("\n--- Optimized Quadruples Table (op, arg1, arg2, result) ---")
    print(TACGenerator.format_quads(optimized_quads))

    print("\n--- Pseudo Assembly Target Code ---")
    print(generate_pseudo_assembly(optimized_quads))

    print(f"\n  Original TAC instructions: {len(quads)}")
    print(f"  Optimized TAC instructions: {len(optimized_quads)}")
    print("\nOptimization and Target Code Generation Successful.")


def main(argv=None):
    """Run lexical, syntactic, semantic, LL(1), and SLR analysis."""
    argv = argv or sys.argv
    source_path = resolve_source_path(argv)

    try:
        code = read_source(source_path)
    except OSError as error:
        print(f"{source_path}: error: {error}")
        return 1

    lexer = Lexer()

    try:
        tokens = lexer.tokenize(code)
        print("Tokens:", [(kind, value) for kind, value, _, _ in tokens])
    except LexerError as error:
        print_error(
            source_path,
            code,
            getattr(error, "line", 1),
            getattr(error, "col", 1),
            getattr(error, "message_only", str(error)),
        )
        return 1

    try:
        parser = Parser(tokens, show_tree=True, show_left=True, show_right=True, show_gui_tree=False)
        root = parser.parse_program()

        if not run_semantic_analysis(root, source_path, code):
            return 1

        # print("\n\n\n LL(1) Table-Driven Parser")
        # print("=" * 60)
        # ll1_parser = LL1Parser()
        # print_first_sets(ll1_parser.first)
        # print_follow_sets(ll1_parser.follow)
        # ll1_parser.print_table()
        # if not ll1_parser.parse(tokens):
        #     return 1

        # print("\n\n\n SLR Table-Driven Shift-Reduce Parser")
        # print("=" * 60)
        # slr_parser = ShiftReduceParser()
        # slr_parser.print_tables()
        # if not slr_parser.parse(tokens):
        #     return 1

        run_tac_generation(root)
        
    except SyntaxErrors as errors:
        for error in errors.errors:
            print_error(
                source_path,
                code,
                getattr(error, "line", 1),
                getattr(error, "col", 1),
                getattr(error, "message_only", str(error)),
            )
        return 1

    return 0


if __name__ == "__main__":
    configure_stdout_logger()
    raise SystemExit(main())
