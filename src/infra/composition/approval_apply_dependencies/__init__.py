"""one `build_<x>_approval_deps(session, ...)`
module per approval-backed service family, each an explicit, module-owned factory producing a
frozen `TDeps` dataclass whose transaction-sensitive fields are bound to whichever `Session` is
supplied. Never a generic, type-keyed registry -- each family's factory is a plain function,
imported and called explicitly at its own registration call site.
"""
