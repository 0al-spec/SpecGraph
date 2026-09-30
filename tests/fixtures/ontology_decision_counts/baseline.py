"""Frozen count blocks from SpecGraph 425078c, with tuple returns for comparison."""


def owner_report_counts(decisions):
    accepted_count = sum(1 for decision in decisions if decision["decision_state"] == "accepted")
    rejected_count = sum(1 for decision in decisions if decision["decision_state"] == "rejected")
    clarification_count = sum(
        1 for decision in decisions if decision["decision_state"] == "needs_clarification"
    )
    return accepted_count, rejected_count, clarification_count


def import_preview_counts(previews):
    accepted_count = sum(1 for preview in previews if preview["decision_state"] == "accepted")
    rejected_count = sum(1 for preview in previews if preview["decision_state"] == "rejected")
    clarification_count = sum(
        1 for preview in previews if preview["decision_state"] == "needs_clarification"
    )
    return accepted_count, rejected_count, clarification_count


def import_v2_counts(reviews):
    accepted_count = sum(1 for review in reviews if review["decision_state"] == "accepted")
    rejected_count = sum(1 for review in reviews if review["decision_state"] == "rejected")
    clarification_count = sum(
        1 for review in reviews if review["decision_state"] == "needs_clarification"
    )
    return accepted_count, rejected_count, clarification_count
