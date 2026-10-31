Feature: A resolved foundation import
  @SG72-PINNED-FOUNDATION
  Scenario: One pinned member extends the released foundation ValueObject
    Given the member imports specgraph.foundation 0.1.0 as sg
    When its source and IR are verified and Entry extends sg:ValueObject
    Then both member capture and dependency closure are verified
    And the context records the resolved import and a verified revision
