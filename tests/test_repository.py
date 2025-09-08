from contextlib import nullcontext as does_not_raise
import logging
import os
import pytest
import subprocess
from unittest import mock

from restic_replica import repository


class TestResticCli:
    """Tests for the class repository.ResticCli"""

    class TestExecuteLiveOutput:
        """Tests for the function _execute_live_output"""

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_args(self, fp, restic_cli_fixture):
            args = ["restic", "snapshots"]
            fp.register(
                args,
                stdout=[
                    "repository a977efd9 opened (version 2, compression level auto)",
                    "ID        Time                 Host          Tags        Paths       Size",
                    "--------------------------------------------------------------------------",
                    "49833392  2025-09-08 15:41:12  oracca.local              /etc/hosts  384 B",
                    "--------------------------------------------------------------------------",
                    "1 snapshots",
                ],
            )
            process = restic_cli_fixture._execute_live_output(args)
            assert process.args == args
            assert process.returncode == 0

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_logger_output(self, fp, caplog, restic_cli_fixture):
            caplog.set_level(logging.INFO)
            args = ["restic", "snapshots"]
            fp.register(
                args,
                stdout=[
                    "repository a977efd9 opened (version 2, compression level auto)",
                    "Warning: at least one source file could not be read",
                    "Fatal: Please specify repository location (-r or --repository-file)",
                ],
            )

            restic_cli_fixture._execute_live_output(args)
            assert caplog.record_tuples == [
                (
                    "restic_replica.repository",
                    logging.INFO,
                    "repository a977efd9 opened (version 2, compression level auto)",
                ),
                (
                    "restic_replica.repository",
                    logging.WARNING,
                    "Warning: at least one source file could not be read",
                ),
                (
                    "restic_replica.repository",
                    logging.ERROR,
                    "Fatal: Please specify repository location (-r or --repository-file)",
                ),
            ]

        @pytest.mark.usefixtures("restic_cli_fixture")
        @pytest.mark.parametrize(
            "returncode, expectation",
            [
                (0, does_not_raise()),
                (1, pytest.raises(subprocess.CalledProcessError)),
                (2, pytest.raises(subprocess.CalledProcessError)),
                (3, does_not_raise()),
                (10, pytest.raises(subprocess.CalledProcessError)),
                (11, pytest.raises(subprocess.CalledProcessError)),
                (12, pytest.raises(subprocess.CalledProcessError)),
                (130, pytest.raises(subprocess.CalledProcessError)),
            ],
        )
        def test_returncodes(self, fp, restic_cli_fixture, returncode, expectation):
            args = ["restic", "snapshots"]
            with expectation:
                fp.register(args, returncode=returncode, stdout=None)
                process = restic_cli_fixture._execute_live_output(args)
                assert process.returncode == returncode

    class TestExecute:
        """Tests for the function execute"""

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_args_copy(self, fp, restic_cli_fixture):
            args = ["snapshots"]
            args_with_restic = ["restic", "snapshots"]
            # register the args, prepending restic path
            fp.register(args_with_restic, stdout=None)
            # pass in the args without restic path prepended
            process = restic_cli_fixture.execute(args)
            # process args should have restic path prepended, original args list should should not be mutated
            assert args != args_with_restic
            assert process.args == args_with_restic

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_class_env_vars(self, fp, restic_cli_fixture):
            environment_vars = {
                "RESTIC_PROGRESS_FPS": "60",
                "RESTIC_PASSWORD": "secret",
            }
            fp.register(["restic", "snapshots"], stdout=None)
            restic_cli_fixture.execute(["snapshots"], environment_vars)
            # existing variable should be set to class value
            assert os.environ["RESTIC_PROGRESS_FPS"] == "0.016667"
            # new variable should be updated
            assert os.environ["RESTIC_PASSWORD"] == "secret"
            # original environment_vars dict should not be mutated
            assert environment_vars == {
                "RESTIC_PROGRESS_FPS": "60",
                "RESTIC_PASSWORD": "secret",
            }

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_output_return(self, fp, restic_cli_fixture):
            fake_stdout = [
                "repository a977efd9 opened (version 2, compression level auto)",
                "ID        Time                 Host          Tags        Paths       Size",
                "--------------------------------------------------------------------------",
                "49833392  2025-09-08 15:41:12  oracca.local              /etc/hosts  384 B",
                "--------------------------------------------------------------------------",
                "1 snapshots",
            ]
            # join the list with os.linesep(), and add trailing separator
            expected_stdout = (os.linesep).join(fake_stdout) + os.linesep
            fp.register(
                ["restic", "snapshots"],
                stdout=fake_stdout,
            )
            process = restic_cli_fixture.execute(["snapshots"])
            assert process.stdout == expected_stdout

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_json(self, fp, restic_cli_fixture):
            fp.register(["restic", "snapshots", "--json"], stdout=None)
            process = restic_cli_fixture.execute(["snapshots"], json=True)
            assert process.args == ["restic", "snapshots", "--json"]

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_live_output(self, restic_cli_fixture):
            fake_return = subprocess.CompletedProcess(["./foo"], 0)
            with mock.patch.object(
                restic_cli_fixture, "_execute_live_output", return_value=fake_return
            ):
                assert (
                    restic_cli_fixture.execute(["snapshots"], live_output=True)
                    == fake_return
                )
