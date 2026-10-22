import logging
import time

from behave import given, then, when

logger = logging.getLogger("sample.streaming")


@given("a step that initializes calculation logger")
def step_init_logger(context):
    logger.info("Starting calculation step 1 initialization...")
    context.step_count = 1


@when("a step logs multiple progress messages with delays")
def step_log_progress(context):
    logger.info("Step 2: Processing batch 1 of calculations...")
    time.sleep(0.2)
    logger.info("Step 2: Processing batch 2 of calculations...")
    time.sleep(0.2)
    logger.warning("Step 2: Completed processing with warning flag set")
    context.step_count += 1


@then("a final step verifies that all previous logs remain visible")
def step_verify_progression(context):
    logger.info("Step 3: Verification reached successfully")
    assert context.step_count == 2
