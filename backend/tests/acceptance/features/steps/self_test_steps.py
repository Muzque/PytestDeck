from behave import given, then, when


@given('PytestDeck backend is running')
def step_backend_running(context):
    pass

@when('a health request is sent')
def step_health_request(context):
    pass

@then('the response status should be 200')
def step_response_status(context):
    pass
