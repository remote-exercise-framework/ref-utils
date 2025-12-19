"""Tests for ref_utils.decorator module."""

import warnings
from dataclasses import asdict
from unittest.mock import patch

import pytest

from ref_utils.decorator import (
    DEFAULT_TASK_NAME,
    TaskTestResult,
    TestResult,
    _Task,
    add_environment_test,
    add_submission_test,
    environment_test,
    extended_submission_test,
    run_tests,
    submission_test,
)
from ref_utils.error import RefUtilsError


def _get_registered_tasks():
    """Access the private __registered_tasks dict from decorator module."""
    # Module-level double underscore names are not mangled
    # Access through __dict__ to avoid attribute access issues
    import ref_utils.decorator as dec_module

    return dec_module.__dict__["__registered_tasks"]


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset the global __registered_tasks dict between tests."""
    registered_tasks = _get_registered_tasks()
    original_tasks = registered_tasks.copy() if registered_tasks else {}
    if registered_tasks is not None:
        registered_tasks.clear()
    yield
    if registered_tasks is not None:
        registered_tasks.clear()
        registered_tasks.update(original_tasks)


class TestTestResult:
    """Tests for TestResult dataclass."""

    def test_success_without_score(self) -> None:
        """Test TestResult with success and no score."""
        result = TestResult(success=True, score=None)
        assert result.success is True
        assert result.score is None

    def test_success_with_score(self) -> None:
        """Test TestResult with success and score."""
        result = TestResult(success=True, score=95.5)
        assert result.success is True
        assert result.score == 95.5

    def test_failure_without_score(self) -> None:
        """Test TestResult with failure and no score."""
        result = TestResult(success=False, score=None)
        assert result.success is False
        assert result.score is None

    def test_to_dict(self) -> None:
        """Test conversion to dict."""
        result = TestResult(success=True, score=100.0)
        d = asdict(result)
        assert d == {"success": True, "score": 100.0}


class TestTask:
    """Tests for _Task internal class."""

    def test_initialization(self) -> None:
        """Test _Task initialization."""
        task = _Task("my_task")
        assert task.name == "my_task"
        assert task.env_tests == []
        assert task.submission_test is None
        assert task.extended_submission_test is None


class TestEnvironmentTestDecorator:
    """Tests for @environment_test decorator."""

    def test_registers_function(self) -> None:
        """Test that decorated function is registered."""

        @environment_test()
        def my_env_test() -> bool:
            return True

        assert DEFAULT_TASK_NAME in _get_registered_tasks()
        task = _get_registered_tasks()[DEFAULT_TASK_NAME]
        assert len(task.env_tests) == 1

    def test_custom_task_name(self) -> None:
        """Test registration with custom task name."""

        @environment_test(task_name="custom_task")
        def my_env_test() -> bool:
            return True

        assert "custom_task" in _get_registered_tasks()
        task = _get_registered_tasks()["custom_task"]
        assert len(task.env_tests) == 1

    def test_multiple_env_tests(self) -> None:
        """Test multiple environment tests for same task."""

        @environment_test()
        def env_test_1() -> bool:
            return True

        @environment_test()
        def env_test_2() -> bool:
            return True

        task = _get_registered_tasks()[DEFAULT_TASK_NAME]
        assert len(task.env_tests) == 2

    def test_function_still_callable(self) -> None:
        """Test that decorated function remains callable."""

        @environment_test()
        def my_env_test() -> bool:
            return True

        assert my_env_test() is True


class TestSubmissionTestDecorator:
    """Tests for @submission_test decorator."""

    def test_registers_function(self) -> None:
        """Test that decorated function is registered."""

        @submission_test()
        def my_submission_test() -> bool:
            return True

        assert DEFAULT_TASK_NAME in _get_registered_tasks()
        task = _get_registered_tasks()[DEFAULT_TASK_NAME]
        assert task.submission_test is not None

    def test_custom_task_name(self) -> None:
        """Test registration with custom task name."""

        @submission_test(task_name="my_task")
        def my_submission_test() -> bool:
            return True

        assert "my_task" in _get_registered_tasks()

    def test_only_one_allowed_per_task(self) -> None:
        """Test that only one submission test per task is allowed."""

        @submission_test()
        def test_1() -> bool:
            return True

        with pytest.raises(RefUtilsError):

            @submission_test()
            def test_2() -> bool:
                return True

    def test_function_still_callable(self) -> None:
        """Test that decorated function remains callable."""

        @submission_test()
        def my_test() -> bool:
            return True

        assert my_test() is True


class TestExtendedSubmissionTestDecorator:
    """Tests for @extended_submission_test decorator."""

    def test_registers_function(self) -> None:
        """Test that decorated function is registered."""

        @extended_submission_test()
        def my_extended_test() -> bool:
            return True

        task = _get_registered_tasks()[DEFAULT_TASK_NAME]
        assert task.extended_submission_test is not None

    def test_only_one_allowed_per_task(self) -> None:
        """Test that only one extended submission test per task is allowed."""

        @extended_submission_test()
        def test_1() -> bool:
            return True

        with pytest.raises(RefUtilsError):

            @extended_submission_test()
            def test_2() -> bool:
                return True


class TestDeprecatedDecorators:
    """Tests for deprecated decorator aliases."""

    def test_add_environment_test_warns(self) -> None:
        """Test that add_environment_test emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            @add_environment_test()
            def my_test() -> bool:
                return True

            assert len(w) == 1
            assert "environment_test" in str(w[0].message)

    def test_add_submission_test_warns(self) -> None:
        """Test that add_submission_test emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            @add_submission_test()
            def my_test() -> bool:
                return True

            assert len(w) == 1
            assert "submission_test" in str(w[0].message)


class TestRunTests:
    """Tests for run_tests function."""

    def test_all_tests_pass(self) -> None:
        """Test run_tests when all tests pass."""

        @environment_test()
        def env_test() -> bool:
            return True

        @submission_test()
        def sub_test() -> bool:
            return True

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert len(results) == 1
        assert results[0].success is True

    def test_env_test_fails(self) -> None:
        """Test run_tests when environment test fails."""

        @environment_test()
        def env_test() -> bool:
            return False

        @submission_test()
        def sub_test() -> bool:
            return True

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert results[0].success is False

    def test_submission_test_fails(self) -> None:
        """Test run_tests when submission test fails."""

        @environment_test()
        def env_test() -> bool:
            return True

        @submission_test()
        def sub_test() -> bool:
            return False

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert results[0].success is False

    def test_submission_test_returns_test_result(self) -> None:
        """Test run_tests with TestResult return type."""

        @environment_test()
        def env_test() -> bool:
            return True

        @submission_test()
        def sub_test() -> TestResult:
            return TestResult(success=True, score=85.5)

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert results[0].success is True
        assert results[0].score == 85.5

    def test_only_run_these_tasks_parameter(self) -> None:
        """Test selective task execution via parameter."""

        @submission_test(task_name="task1")
        def test_1() -> bool:
            return True

        @submission_test(task_name="task2")
        def test_2() -> bool:
            return True

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests(only_run_these_tasks=["task1"])

        # Only task1 should have been run
        task_names = [r.task_name for r in results]
        assert "task1" in task_names

    def test_env_test_without_submission_test_raises(self) -> None:
        """Test that environment test without submission test raises error."""

        @environment_test()
        def env_test() -> bool:
            return True

        with pytest.raises(RefUtilsError):
            with patch("ref_utils.decorator.print_ok"):
                run_tests()

    def test_no_submission_test_succeeds(self) -> None:
        """Test that task with no submission test still succeeds."""

        # Create a task with no tests via direct manipulation
        _get_registered_tasks()["empty_task"] = _Task("empty_task")

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert any(r.task_name == "empty_task" and r.success for r in results)

    def test_submission_test_raises_exception(self) -> None:
        """Test handling of RefUtilsError in submission test."""

        @environment_test()
        def env_test() -> bool:
            return True

        @submission_test()
        def sub_test() -> bool:
            raise RefUtilsError("Test error")

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert results[0].success is False

    def test_env_test_must_return_bool(self) -> None:
        """Test that environment test must return bool."""

        @environment_test()
        def env_test() -> str:
            return "not a bool"  # type: ignore

        @submission_test()
        def sub_test() -> bool:
            return True

        with pytest.raises(RefUtilsError):
            with patch("ref_utils.decorator.print_ok"):
                run_tests()

    def test_returns_task_test_result_list(self) -> None:
        """Test that run_tests returns a list of TaskTestResult."""

        @submission_test()
        def sub_test() -> bool:
            return True

        with patch("ref_utils.decorator.print_ok"):
            with patch("ref_utils.decorator.print_err"):
                results = run_tests()

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], TaskTestResult)
