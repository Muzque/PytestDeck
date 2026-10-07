Feature: Test Discovery API

  Scenario: Discovering tests in the target unit test suite
    Given PytestDeck backend is running
    When a discover request is sent for suite "tests/unit"
    Then the discover response status should be 200
    And the discovered root tree should exist

  Scenario: Discovering tests in the target integration test suite
    Given PytestDeck backend is running
    When a discover request is sent for suite "tests/integration"
    Then the discover response status should be 200
    And the discovered tree total nodes should be greater than 0
    And the discovered root tree should exist

  Scenario: Discovering feature files in the target acceptance test suite
    Given PytestDeck backend is running
    When a discover request is sent for suite "tests/acceptance"
    Then the discover response status should be 200
    And the discovered tree total nodes should be greater than 0
    And the discovered root tree should exist

  Scenario: Fetching test method details and docstring
    Given PytestDeck backend is running
    When a test detail request is sent for node "tests/acceptance/features/calculator.feature::Addition of two numbers"
    Then the test detail response status should be 200
    And the test detail name should be "Addition of two numbers"
    And the test detail type should be "scenario"

