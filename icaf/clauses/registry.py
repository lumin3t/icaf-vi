def _get_registry():
    """
    Lazy registry — clause modules are only imported when actually needed.
    This prevents transitive import errors at startup.
    """
    from icaf.clauses.clause_1_1_1.clause import Clause_1_1_1
    from icaf.clauses.clause_1_6_1.clause import Clause_1_6_1
    from icaf.clauses.clause_1_2_4.clause import Clause_1_2_4
    from icaf.clauses.clause_1_6_5.clause_1_6_5_clause import Clause_1_6_5

    return {
        "1.1.1": Clause_1_1_1,
        "1.6.1": Clause_1_6_1,
        "1.2.4": Clause_1_2_4,
        "1.6.5": Clause_1_6_5,
    }


# Keep CLAUSE_REGISTRY as a dict-like proxy for backward compatibility
class _LazyRegistry(dict):
    def __missing__(self, key):
        # Trigger full load if key not found
        self.update(_get_registry())
        if key in self:
            return self[key]
        raise KeyError(f"Clause {key!r} not registered")

    def __contains__(self, key):
        if not dict.__len__(self):
            self.update(_get_registry())
        return dict.__contains__(self, key)


CLAUSE_REGISTRY = _LazyRegistry()
