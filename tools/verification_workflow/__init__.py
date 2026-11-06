"""Pure verification workflow contracts; no process runner, CLI or admission authority.

Adapters must independently establish the supplied facts, allocate run identities,
protect run-local outputs and persist the terminal result atomically. These types
and policies check consistency; constructing a record does not prove execution.
"""
