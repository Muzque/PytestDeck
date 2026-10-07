Feature: Calculator Operations
  As a math user
  I want to perform arithmetic operations
  So that I get accurate calculation results

  @smoke
  Scenario: Addition of two numbers
    Given I have a calculator
    When I add 5 and 7
    Then the result should be 12

  Scenario: Division of two numbers
    Given I have a calculator
    When I divide 20 by 4
    Then the result should be 5

  @slow
  Scenario: Long running calculation sequence
    Given I have a calculator
    When I add 100 and 200
    And I add 300 and 400
    Then the result should be 700

  Scenario Outline: Parameterized arithmetic verification
    Given I have a calculator
    When I add <a> and <b>
    Then the result should be <expected>

    Examples:
      | a   | b   | expected |
      | 1   | 2   | 3        |
      | 15  | 25  | 40       |
      | 50  | 50  | 100      |
