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
        "\n"
        "1 feature passed, 2 scenarios passed\n"
    )

    collector = MethodOutputCollector()
    for line in text.splitlines(keepends=True):
        collector.process_line(line)

    results = collector.get_results()
    assert "features/login.feature::Successful login" in results
    assert "LOG: user verified" in results["features/login.feature::Successful login"]["output"]
    assert "features/login.feature::Invalid login" in results


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
