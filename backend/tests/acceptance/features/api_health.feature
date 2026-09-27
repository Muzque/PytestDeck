Feature: API Health and Configuration

  Scenario: Health check endpoint responds cleanly
    Given PytestDeck backend is running
    When a health request is sent
    Then the response status should be 200

  Scenario: Fetching target repository configuration
    Given PytestDeck backend is running
    When a config request is sent
    Then the config response status should be 200
    And the config response should contain "config"
