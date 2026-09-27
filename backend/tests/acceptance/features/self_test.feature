Feature: Self Execution & Discovery
  Scenario: Health check endpoint responds cleanly
    Given PytestDeck backend is running
    When a health request is sent
    Then the response status should be 200
