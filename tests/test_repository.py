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
        """Tests for the _execute_live_output method"""

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_args(self, fp, restic_cli_fixture):
            """arguments should be passed through to the process"""
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
            """output from the process should be emitted to logger line by line"""
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
            """exit codes 0 and 3 should not raise an Exception, all other exit codes should"""
            args = ["restic", "snapshots"]
            with expectation:
                fp.register(args, returncode=returncode, stdout=None)
                process = restic_cli_fixture._execute_live_output(args)
                assert process.returncode == returncode

    class TestExecute:
        """Tests for the execute method"""

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_args_copy(self, fp, restic_cli_fixture):
            """input arguments should not be mutated"""
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
            """
            environment variables should be set, with the ResticCli fixture environment
            variables having primacy. The input ductionary should not be mutated.
            """
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
            """output from the command should be returned"""
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
            """the json parameter should be appended to the arguments"""
            fp.register(["restic", "snapshots", "--json"], stdout=None)
            process = restic_cli_fixture.execute(["snapshots"], json=True)
            assert process.args == ["restic", "snapshots", "--json"]

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_verbose(self, fp, restic_cli_fixture):
            """the verbose parameter should be appended to the arguments"""
            restic_cli_fixture.verbose = 1
            fp.register(["restic", "snapshots", "--verbose=1"], stdout=None)
            process = restic_cli_fixture.execute(["snapshots"])
            assert process.args == ["restic", "snapshots", "--verbose=1"]

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_live_output(self, restic_cli_fixture):
            """the live output process should return a populated CompletedProcess instance"""
            fake_return = subprocess.CompletedProcess(["./foo"], 0)
            with mock.patch.object(
                restic_cli_fixture, "_execute_live_output", return_value=fake_return
            ):
                assert (
                    restic_cli_fixture.execute(["snapshots"], live_output=True)
                    == fake_return
                )


class TestRepository:
    """Tests for the class repository.Repository"""

    class TestInit:
        """Tests for the __init__ method"""

        @pytest.mark.usefixtures("repository_fixture")
        def test_environment_vars_merge(self, repository_fixture):
            """
            supplied password should result in the correct environment variable being
            appended to the existing environment variables dictionary.
            """
            assert repository_fixture.environment_vars == {
                "RESTIC_COMPRESSION": "true",
                "RESTIC_PASSWORD": "secret",
            }

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_password_file_environment_var(self, restic_cli_fixture):
            """supplied password file should result in the correct environment variable being set"""
            myrepo = repository.Repository(
                "/tmp/myrepo",
                "myrepo",
                restic_cli_fixture,
                password_file="/path/to/password-file",
            )
            assert myrepo.environment_vars == {
                "RESTIC_PASSWORD_FILE": "/path/to/password-file"
            }

        @pytest.mark.usefixtures("restic_cli_fixture")
        def test_password_command_environment_var(self, restic_cli_fixture):
            """supplied password command should result in the correct environment variable being set"""
            myrepo = repository.Repository(
                "/tmp/myrepo",
                "myrepo",
                restic_cli_fixture,
                password_command="/path/to/password-command",
            )
            assert myrepo.environment_vars == {
                "RESTIC_PASSWORD_COMMAND": "/path/to/password-command"
            }

    class TestVerifyPasswordIsSet:
        """Tests for the _verify_password_is_set method"""

        @pytest.mark.usefixtures("repository_fixture")
        def test_password(self, repository_fixture):
            """A set password should return true"""
            assert repository_fixture._verify_password_is_set() is True

        @pytest.mark.usefixtures("repository_fixture")
        def test_password_file(self, repository_fixture):
            """A set password_file should return true"""
            repository_fixture.password_file = "/path/to/password-file"
            repository_fixture.password = None
            assert repository_fixture._verify_password_is_set() is True

        @pytest.mark.usefixtures("repository_fixture")
        def test_password_command(self, repository_fixture):
            """A set password_command should return true"""
            repository_fixture.password_command = "/path/to/password-command"
            repository_fixture.password = None
            assert repository_fixture._verify_password_is_set() is True

        @pytest.mark.usefixtures("repository_fixture")
        def test_password_file_warning(self, repository_fixture, caplog):
            """A set password and password_file should return True but emit a warning to logger"""
            repository_fixture.password_file = "/path/to/password-file"
            assert repository_fixture._verify_password_is_set() is True
            assert caplog.record_tuples[0] == (
                "restic_replica.repository",
                30,
                f"password and password_file were specified for repository {repository_fixture.uri}; password_file will be used",
            )

        @pytest.mark.usefixtures("repository_fixture")
        def test_password_command_warning(self, repository_fixture, caplog):
            """A set password and password_command should return True but emit a warning to logger"""
            repository_fixture.password_command = "/path/to/password-command"
            assert repository_fixture._verify_password_is_set() is True
            assert caplog.record_tuples[0] == (
                "restic_replica.repository",
                30,
                f"password and password_command were specified for repository {repository_fixture.uri}; password_command will be used",
            )

        @pytest.mark.usefixtures("repository_fixture")
        def test_password_file_and_command(self, repository_fixture):
            """A set password_file and password_command should raise a KeyError exception"""
            repository_fixture.password_file = "/path/to/password-file"
            repository_fixture.password_command = "/path/to/password-command"
            repository_fixture.password = None
            with pytest.raises(KeyError):
                repository_fixture._verify_password_is_set()

        @pytest.mark.usefixtures("repository_fixture")
        def test_no_password_attributes(self, repository_fixture):
            """If no password* attribute is set, a ValueError exception should be raised"""
            repository_fixture.password = None
            with pytest.raises(ValueError):
                repository_fixture._verify_password_is_set()

    class TestSnapshots:
        """Tests for the snapshots method"""

        def return_args(self, *args, **kwargs):
            """function that returns all args passed to it"""
            return args

        def return_kwargs(self, *args, **kwargs):
            """function that returns all kwargs passed to it"""
            return kwargs

        @pytest.mark.usefixtures("repository_fixture")
        def test_args(self, repository_fixture):
            """args should include _common_args and have `snapshots` appended"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_args,
            ):
                assert repository_fixture.snapshots() == (
                    [
                        "-r",
                        f"{repository_fixture.uri}",
                        "snapshots",
                    ],
                )

        @pytest.mark.usefixtures("repository_fixture")
        def test_environment_vars(self, repository_fixture):
            """environment vars should be passed as-is to restic_cli"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                assert (
                    repository_fixture.snapshots()["environment_vars"]
                    == repository_fixture.environment_vars
                )

        @pytest.mark.usefixtures("repository_fixture")
        def test_live_output(self, repository_fixture):
            """live_output var should be set to false by default"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                assert repository_fixture.snapshots()["live_output"] is False
                assert (
                    repository_fixture.snapshots(live_output=True)["live_output"]
                    is True
                )

        @pytest.mark.usefixtures("repository_fixture")
        def test_json(self, repository_fixture):
            """json var should be set to false by default"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                assert repository_fixture.snapshots()["json"] is False
                assert repository_fixture.snapshots(json=True)["json"] is True

    class TestCopy:
        """Tests for the copy method"""

        def return_args(self, *args, **kwargs):
            """function that returns all args passed to it"""
            return args

        def return_kwargs(self, *args, **kwargs):
            """function that returns all kwargs passed to it"""
            return kwargs

        @pytest.fixture
        @pytest.mark.usefixtures("restic_cli_fixture")
        def other_repository_fixture(self, restic_cli_fixture):
            """Return a (:class:`repository.Repository`) instance"""
            return repository.Repository(
                "/tmp/repo2", "repo2", restic_cli_fixture, "secret2"
            )

        @pytest.mark.usefixtures("repository_fixture")
        def test_same_repository(self, repository_fixture):
            """if the same repository is set as both source and destination a RuntimeError should be raised"""
            with pytest.raises(RuntimeError):
                repository_fixture.copy(repository_fixture)

        @pytest.mark.usefixtures("repository_fixture", "other_repository_fixture")
        def test_args(self, repository_fixture, other_repository_fixture):
            """args should include _common_args and have `copy` and second repository appended"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_args,
            ):
                assert repository_fixture.copy(other_repository_fixture) == (
                    [
                        "-r",
                        f"{repository_fixture.uri}",
                        "copy",
                        "--from-repo",
                        f"{other_repository_fixture.uri}",
                    ],
                )

        @pytest.mark.usefixtures("repository_fixture", "other_repository_fixture")
        def test_other_password(self, repository_fixture, other_repository_fixture):
            """environment vars should be passed as-is to restic_cli, but RESTIC_FROM_PASSWORD should also be set"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                expected_environment_vars = {}
                expected_environment_vars.update(repository_fixture.environment_vars)
                expected_environment_vars["RESTIC_FROM_PASSWORD"] = (
                    other_repository_fixture.password
                )
                assert (
                    repository_fixture.copy(other_repository_fixture)[
                        "environment_vars"
                    ]
                    == expected_environment_vars
                )

        @pytest.mark.usefixtures("repository_fixture", "other_repository_fixture")
        def test_other_password_file(
            self, repository_fixture, other_repository_fixture
        ):
            """environment vars should be passed as-is to restic_cli, but RESTIC_FROM_PASSWORD_FILE should also be set"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                other_repository_fixture.password_file = "/path/to/password-file2"
                expected_environment_vars = {}
                expected_environment_vars.update(repository_fixture.environment_vars)
                expected_environment_vars["RESTIC_FROM_PASSWORD_FILE"] = (
                    other_repository_fixture.password_file
                )
                assert (
                    repository_fixture.copy(other_repository_fixture)[
                        "environment_vars"
                    ]
                    == expected_environment_vars
                )

        @pytest.mark.usefixtures("repository_fixture", "other_repository_fixture")
        def test_other_password_command(
            self, repository_fixture, other_repository_fixture
        ):
            """environment vars should be passed as-is to restic_cli, but RESTIC_FROM_PASSWORD_COMMAND should also be set"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                other_repository_fixture.password_command = "/path/to/password-command2"
                expected_environment_vars = {}
                expected_environment_vars.update(repository_fixture.environment_vars)
                expected_environment_vars["RESTIC_FROM_PASSWORD_COMMAND"] = (
                    other_repository_fixture.password_command
                )
                assert (
                    repository_fixture.copy(other_repository_fixture)[
                        "environment_vars"
                    ]
                    == expected_environment_vars
                )

        @pytest.mark.usefixtures("repository_fixture", "other_repository_fixture")
        def test_live_output(self, repository_fixture, other_repository_fixture):
            """live_output should be set to false by default"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                assert (
                    repository_fixture.copy(other_repository_fixture)["live_output"]
                    is False
                )
                assert (
                    repository_fixture.copy(other_repository_fixture, live_output=True)[
                        "live_output"
                    ]
                    is True
                )

        @pytest.mark.usefixtures("repository_fixture", "other_repository_fixture")
        def test_json(self, repository_fixture, other_repository_fixture):
            """json should be set to false by default"""
            with mock.patch.object(
                repository_fixture.restic_cli,
                "execute",
                self.return_kwargs,
            ):
                assert (
                    repository_fixture.copy(other_repository_fixture)["json"] is False
                )
                assert (
                    repository_fixture.copy(other_repository_fixture, json=True)["json"]
                    is True
                )
