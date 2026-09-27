Feature: Test Discovery API

  Scenario: Discovering tests in the backend unit test suite
    Given PytestDeck backend is running
    When a discover request is sent for suite "backend/tests/unit"
    Then the discover response status should be 200
    And the discovered root tree should exist

  Scenario: Discovering tests in the backend integration test suite
    Given PytestDeck backend is running
    When a discover request is sent for suite "backend/tests/integration"
    Then the discover response status should be 200
    And the discovered tree total nodes should be greater than 0
    And the discovered root tree should exist

  Scenario: Discovering feature files in the backend acceptance test suite
    Given PytestDeck backend is running
    When a discover request is sent for suite "backend/tests/acceptance"
    Then the discover response status should be 200
    And the discovered tree total nodes should be greater than 0
    And the discovered root tree should exist
