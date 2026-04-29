"""Scoped symbol-table support for semantic analysis."""

from dataclasses import dataclass, field


TYPE_SIZES = {
    "int": 4,
    "float": 8,
}


@dataclass
class SymbolEntry:
    """Store the semantic information associated with one identifier."""

    name: str
    var_type: str
    scope_name: str
    scope_level: int
    offset: int
    line: int
    col: int


@dataclass
class _ScopeFrame:
    """Represent one active lexical scope in the scope stack."""

    name: str
    level: int
    symbols: dict = field(default_factory=dict)
    next_offset: int = 0


class SymbolTable:
    """Manage nested lexical scopes and per-scope symbol offsets."""

    def __init__(self):
        self.scopes = []

    def enter_scope(self, name):
        """Push a new scope frame onto the active scope stack."""
        frame = _ScopeFrame(name=name, level=len(self.scopes))
        self.scopes.append(frame)
        return frame

    def exit_scope(self):
        """Pop and return the innermost active scope frame."""
        if not self.scopes:
            raise RuntimeError("cannot exit scope: no active scope")
        return self.scopes.pop()

    def lookup_current_scope(self, name):
        """Return an identifier from the current scope, if it exists."""
        if not self.scopes:
            return None
        return self.scopes[-1].symbols.get(name)

    def lookup(self, name):
        """Resolve an identifier from the innermost scope outward."""
        for frame in reversed(self.scopes):
            entry = frame.symbols.get(name)
            if entry is not None:
                return entry
        return None

    def insert(self, name, var_type, line, col):
        """Insert an identifier into the current scope and assign its offset."""
        if not self.scopes:
            raise RuntimeError("cannot insert symbol: no active scope")

        frame = self.scopes[-1]
        if name in frame.symbols:
            return None

        entry = SymbolEntry(
            name=name,
            var_type=var_type,
            scope_name=frame.name,
            scope_level=frame.level,
            offset=frame.next_offset,
            line=line,
            col=col,
        )
        frame.symbols[name] = entry
        frame.next_offset += TYPE_SIZES[var_type]
        return entry

    def snapshot_active_scopes(self):
        """Return a flat view of symbols from all currently active scopes."""
        snapshot = []
        for frame in self.scopes:
            snapshot.extend(frame.symbols.values())
        return snapshot
