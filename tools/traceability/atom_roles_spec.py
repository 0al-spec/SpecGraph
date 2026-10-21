"""RFC 0226: criterion and policy roles account for the complete atom inventory."""

from specification_core import PredicateSpec

from .context import AtomRolesFacts

ATOM_ROLES_SPEC: PredicateSpec[AtomRolesFacts] = PredicateSpec(
    lambda c: c.inventory_atom_ids == c.criterion_atom_ids | c.policy_atom_ids,
    name="trace.atom_roles_complete",
)
