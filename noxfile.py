import nox


@nox.session(python=["3.11", "3.12", "3.13", "3.14"], venv_backend="uv")
def tests(session) -> None:
    session.run_install(
        "uv",
        "sync",
        "--only-dev",
        "--locked",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )
    session.run("uv", "run", "pytest")
