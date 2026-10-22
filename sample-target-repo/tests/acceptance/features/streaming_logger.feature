Feature: Streaming Logger and Step Progression
  As a developer using PytestDeck
  I want to see each acceptance step preserved and logger output streamed in real time
  So that long-running step logs are not overwritten or hidden until failure

  @streaming
  Scenario: Sequential steps with live logging progression
    Given a step that initializes calculation logger
    When a step logs multiple progress messages with delays
    Then a final step verifies that all previous logs remain visible
