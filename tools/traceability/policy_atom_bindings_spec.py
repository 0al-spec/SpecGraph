"""RFC 0226: every distinct policy atom has exactly one authored binding."""

from collections import Counter

from specification_core import PredicateSpec

from .context import PolicyAtomBindingsFacts

POLICY_ATOM_BINDINGS_SPEC: PredicateSpec[PolicyAtomBindingsFacts] = PredicateSpec(
    lambda c: (
        Counter(c.bound_atom_ids) == Counter(c.declared_atom_ids)
        and len(c.declared_atom_ids) == len(set(c.declared_atom_ids))
    ),
    name="trace.policy_atom_bindings_complete",
)
