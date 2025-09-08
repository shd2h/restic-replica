import pytest

from restic_replica.repository import Repository


@pytest.fixture
def repository_fixture(restic_cli_fixture):
    """Return a (:class:`repository.Repository`) instance"""
    return Repository(
        "/tmp/restic-repo",
        "myrepo",
        restic_cli_fixture,
        password="secret",
        environment_vars={"RESTIC_COMPRESSION": "true"},
    )
