from infrastructure.output_splitter import MethodOutputCollector


def test_single_targeted_node_output():
    node_id = "backend/tests/integration/test_api.py::test_case_a"
    collector = MethodOutputCollector(requested_nodes=[node_id])

    collector.process_line("Started process uv run pytest ...\n")
    collector.process_line("DEBUG: testing connection\n")
    collector.process_line("backend/tests/integration/test_api.py::test_case_a PASSED\n")

    results = collector.get_results()
    assert node_id in results
    assert results[node_id]["outcome"] == "passed"
    assert "DEBUG: testing connection" in results[node_id]["output"]


def test_multi_node_pytest_output_segmentation():
    text = (
        "============================= test session starts ==============================\n"
        "rootdir: /tmp\n"
        "tests/test_x.py::test_one [INFO] step 1\n"
        "result from step 1\n"
        "PASSED\n"
        "tests/test_x.py::test_two [INFO] step 2\n"
        "FAILED\n"
        "FAILURES\n"
        "___________________________________ test_two ___________________________________\n"
        ">   assert False\n"
        "E   assert False\n"
        "tests/test_x.py:12: AssertionError\n"
        "=========================== 1 failed, 1 passed in 0.20s ===========================\n"
    )

    collector = MethodOutputCollector()
    for line in text.splitlines(keepends=True):
        collector.process_line(line)

    results = collector.get_results()
    assert "tests/test_x.py::test_one" in results
    assert results["tests/test_x.py::test_one"]["outcome"] == "passed"
    assert "[INFO] step 1" in results["tests/test_x.py::test_one"]["output"]

    assert "tests/test_x.py::test_two" in results
    assert results["tests/test_x.py::test_two"]["outcome"] == "failed"
    assert "AssertionError" in results["tests/test_x.py::test_two"]["output"]


def test_behave_scenario_output_segmentation():
    text = (
        "Feature: Login # features/login.feature:1\n"
        "\n"
        "  Scenario: Successful login # features/login.feature:3\n"
        "    Given valid user\n"
        "    LOG: user verified\n"
        "    Then 200 OK\n"
        "\n"
        "  Scenario: Invalid login # features/login.feature:8\n"
        "    Given invalid user\n"
        "    Then 401 Unauthorized\n"
        "      Assertion Failed: expected 401 got 500\n"
        "\n"
        "0 features passed, 1 failed, 0 skipped\n"
        "1 scenario passed, 1 failed, 0 skipped\n"
    )

    collector = MethodOutputCollector()
    for line in text.splitlines(keepends=True):
        collector.process_line(line)

    results = collector.get_results()
    assert "features/login.feature::Successful login" in results
    assert "LOG: user verified" in results["features/login.feature::Successful login"]["output"]
    assert results["features/login.feature::Successful login"]["outcome"] == "passed"
    assert "features/login.feature::Invalid login" in results
    assert results["features/login.feature::Invalid login"]["outcome"] == "failed"


def test_class_targeting_not_single_leaf():
    class_node = "tests/test_service.py::TestService"
    collector = MethodOutputCollector(requested_nodes=[class_node])
    assert not collector.is_single_node

    collector.process_line("tests/test_service.py::TestService::test_one PASSED [ 50%]\n")
    collector.process_line("tests/test_service.py::TestService::test_two PASSED [100%]\n")
    results = collector.get_results()
    assert "tests/test_service.py::TestService::test_one" in results
    assert "tests/test_service.py::TestService::test_two" in results


def test_merge_json_report_stage_durations():
    collector = MethodOutputCollector()
    report = {
        "tests": [
            {
                "nodeid": "tests/test_foo.py::test_with_fixtures",
                "outcome": "passed",
                "setup": {"duration": 0.0012, "outcome": "passed"},
                "call": {"duration": 0.0004, "outcome": "passed"},
                "teardown": {"duration": 0.0001, "outcome": "passed"},
            },
            {
                "nodeid": "tests/test_foo.py::test_setup_failure",
                "outcome": "failed",
                "setup": {"duration": 0.0025, "outcome": "failed"},
                "call": None,
                "teardown": {"duration": 0.0002, "outcome": "passed"},
            },
        ]
    }
    collector.merge_json_report(report)
    res = collector.get_results()

    assert "tests/test_foo.py::test_with_fixtures" in res
    assert res["tests/test_foo.py::test_with_fixtures"]["duration"] == round(0.0012 + 0.0004 + 0.0001, 4)
    assert res["tests/test_foo.py::test_setup_failure"]["duration"] == round(0.0025 + 0.0002, 4)


def test_dotted_class_failure_output():
    text = (
        "tests/test_cls.py::TestClass::test_broken FAILED [100%]\n"
        "FAILURES\n"
        "_____________________________ TestClass.test_broken _____________________________\n"
        "def test_broken(self):\n"
        ">   raise ValueError('custom message')\n"
        "E   ValueError: custom message\n"
        "tests/test_cls.py:10: ValueError\n"
        "=========================== short test summary info ============================\n"
    )
    collector = MethodOutputCollector()
    for line in text.splitlines(keepends=True):
        collector.process_line(line)

    results = collector.get_results()
    assert "tests/test_cls.py::TestClass::test_broken" in results
    out = results["tests/test_cls.py::TestClass::test_broken"]["output"]
    assert "ValueError: custom message" in out


def test_merge_json_report_enriches_captured_output():
    collector = MethodOutputCollector()
    collector.process_line("tests/test_p.py::test_logging PASSED [100%]\n")

    report = {
        "tests": [
            {
                "nodeid": "tests/test_p.py::test_logging",
                "outcome": "passed",
                "call": {
                    "duration": 0.005,
                    "outcome": "passed",
                    "stdout": "Log line 1\nLog line 2\nLog line 3\n",
                    "stderr": "Warning: cache miss\n",
                },
            }
        ]
    }
    collector.merge_json_report(report)
    res = collector.get_results()
    output = res["tests/test_p.py::test_logging"]["output"]
    assert "Log line 1" in output
    assert "Log line 2" in output
    assert "Warning: cache miss" in output


def test_parametrized_special_chars_and_canonical_node_id_merge():
    collector = MethodOutputCollector(requested_nodes=["tests/unit/test_calculator.py"])
    collector.process_line(
        "tests/unit/test_calculator.py::test_add_with_custom_ids[1 + 2 = 3 (positive)] PASSED [ 50%]\n"
    )
    collector.process_line(
        "tests/unit/test_calculator.py::test_add_with_custom_ids[a=-4, b=10 -> 6] PASSED [100%]\n"
    )

    report = {
        "tests": [
            {
                "nodeid": "test_calculator.py::test_add_with_custom_ids[1 + 2 = 3 (positive)]",
                "outcome": "passed",
                "call": {"duration": 0.1234, "outcome": "passed"},
            },
            {
                "nodeid": "test_calculator.py::test_add_with_custom_ids[a=-4, b=10 -> 6]",
                "outcome": "passed",
                "call": {"duration": 0.2345, "outcome": "passed"},
            },
        ]
    }
    collector.merge_json_report(report)
    res = collector.get_results()

    k1 = "tests/unit/test_calculator.py::test_add_with_custom_ids[1 + 2 = 3 (positive)]"
    k2 = "tests/unit/test_calculator.py::test_add_with_custom_ids[a=-4, b=10 -> 6]"
    assert k1 in res
    assert k2 in res
    assert res[k1]["outcome"] == "passed"
    assert res[k1]["duration"] == 0.1234
    assert res[k2]["outcome"] == "passed"
    assert res[k2]["duration"] == 0.2345
    assert "tests/unit/test_calculator.py::test_add_with_custom_ids[1" not in res
    assert "tests/unit/test_calculator.py::test_add_with_custom_ids[a" not in res
    assert "test_calculator.py::test_add_with_custom_ids[1 + 2 = 3 (positive)]" not in res


def test_merge_json_report_does_not_steal_duration_across_same_named_functions():
    collector = MethodOutputCollector(requested_nodes=["tests/unit"])
    collector.process_line("tests/unit/extra_test_calc.py::test_add PASSED [ 33%]\n")
    collector.process_line("tests/unit/sub/test_calc.py::test_add PASSED [ 66%]\n")
    collector.process_line("tests/unit/test_calc.py::test_add PASSED [100%]\n")

    report = {
        "tests": [
            {
                "nodeid": "test_calc.py::test_add",
                "outcome": "passed",
                "call": {"duration": 0.1111, "outcome": "passed"},
            },
            {
                "nodeid": "extra_test_calc.py::test_add",
                "outcome": "passed",
                "call": {"duration": 0.2222, "outcome": "passed"},
            },
            {
                "nodeid": "sub/test_calc.py::test_add",
                "outcome": "passed",
                "call": {"duration": 0.3333, "outcome": "passed"},
            },
        ]
    }
    collector.merge_json_report(report)
    res = collector.get_results()

    assert res["tests/unit/test_calc.py::test_add"]["duration"] == 0.1111
    assert res["tests/unit/extra_test_calc.py::test_add"]["duration"] == 0.2222
    assert res["tests/unit/sub/test_calc.py::test_add"]["duration"] == 0.3333


def test_behave_scenario_and_outline_accumulate_step_durations():
    text = (
        "Feature: Calculator Operations # tests/acceptance/features/calculator.feature:1\n"
        "  Scenario: Addition of two numbers  # tests/acceptance/features/calculator.feature:7\n"
        "    Given I have a calculator        # tests/acceptance/steps/calculator_steps.py:4 0.050s\n"
        "    When I add 5 and 7               # tests/acceptance/steps/calculator_steps.py:9 0.120s\n"
        "    Then the result should be 12     # tests/acceptance/steps/calculator_steps.py:19 0.030s\n"
        "\n"
        "  Scenario Outline: Parameterized arithmetic verification -- @1.1   # tests/acceptance/features/calculator.feature:31\n"
        "    Given I have a calculator                                       # tests/acceptance/steps/calculator_steps.py:4 0.010s\n"
        "    When I add 1 and 2                                              # tests/acceptance/steps/calculator_steps.py:9 0.040s\n"
        "  Scenario Outline: Parameterized arithmetic verification -- @1.2   # tests/acceptance/features/calculator.feature:32\n"
        "    Given I have a calculator                                       # tests/acceptance/steps/calculator_steps.py:4 0.020s\n"
        "    When I add 15 and 25                                            # tests/acceptance/steps/calculator_steps.py:9 0.080s\n"
        "1 feature passed, 0 failed, 0 skipped\n"
    )
    collector = MethodOutputCollector()
    for line in text.splitlines(keepends=True):
        collector.process_line(line)

    res = collector.get_results()
    s1 = "tests/acceptance/features/calculator.feature::Addition of two numbers"
    s2 = "tests/acceptance/features/calculator.feature::Parameterized arithmetic verification"
    assert s1 in res
    assert res[s1]["outcome"] == "passed"
    assert res[s1]["duration"] == 0.2
    assert s2 in res
    assert res[s2]["outcome"] == "passed"
    assert res[s2]["duration"] == 0.15

