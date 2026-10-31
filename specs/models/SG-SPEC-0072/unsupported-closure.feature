Feature: Context verification with an imported ontology package

  @SG72-UNSUPPORTED-CLOSURE
  Scenario: A verified member cannot establish dependency closure
    Given the selection pins one package that imports another ontology
    And the compiler verifies the selected package against its saved IR
    When the required dependency closure check is unsupported
    Then the overall context outcome is unavailable
    And the report retains the successful member check and the missing closure guarantee for that package
