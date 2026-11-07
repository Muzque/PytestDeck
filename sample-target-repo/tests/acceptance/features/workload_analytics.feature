Feature: Workload Analytics and Clamping Operations
  As a data analyst using the Calculator service
  I want to compute powers, remainders, percentages, and clamped metrics
  So that batch pipelines produce bounded and accurate summaries

  Scenario: Computing power and modulo in batch pipeline
    Given I have a calculator
    When I raise 2 to the power of 8
    Then the result should be 256
    When I compute the modulo of 256 by 10
    Then the result should be 6

  Scenario: Clamping out-of-range sensor metrics
    Given I have a calculator
    When I clamp the sensor reading 145.5 between 0 and 100
    Then the result should be 100

  Scenario: Calculating percentage growth across quarters
    Given I have a calculator
    When I compute the percentage of 75 out of 300
    Then the result should be 25
