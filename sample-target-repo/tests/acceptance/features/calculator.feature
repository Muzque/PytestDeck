Feature: Calculator Operations

  Scenario: Addition of two numbers
    Given I have a calculator
    When I add 5 and 7
    Then the result should be 12

  Scenario: Division of two numbers
    Given I have a calculator
    When I divide 20 by 4
    Then the result should be 5
