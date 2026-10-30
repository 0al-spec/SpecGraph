# Illustrative synthetic declaration for a bounded partial model.
# This file is not execution evidence or a claim of complete source coverage.
Feature: Project ontology context mixed outcome

  @SG72-MIXED
  Scenario: Duplicate identity takes precedence over a missing compiler
    Given the selected context repeats one package identity
    And the required compiler is unavailable
    When the selection and compiler check results are combined
    Then the overall outcome is invalid
    And the selection check outcome is invalid
    And the compiler check outcome is unavailable
    And both checks retain their own diagnostics
