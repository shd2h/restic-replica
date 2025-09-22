# restic-replica
The current project status should be considered as "alpha". While the tool is in a usable state, not all planned core functionality has been implemented yet, and the cli may change.

## Info
A command line tool to copy snapshots between Restic repositories, written in python.  
What is Restic? An awesome [backup tool](https://restic.readthedocs.io/).  
Why? Restic does not natively support configuration files.  

## Installation

```console
pip install restic_replica*.whl
```

## Usage

1) [Initialize](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html) both the intended source and destination repositories using Restic, if they have not been already initialized.   
Note: Make sure to use `--copy-chunker-params` when [initializing the destination repository](https://restic.readthedocs.io/en/stable/045_working_with_repos.html#ensuring-deduplication-for-copied-snapshots).
2) Make sure at least one [backup](https://restic.readthedocs.io/en/stable/040_backup.html) has been stored in the source repository.
3) Run restic-replica once to generate an empty configuration file.
```console
❯ restic-replica
ERROR: Missing configuration file
An example configuration file has been created at /home/user/.restic-replica/config.toml. Update the configuration in this file to match your system, and then re-run this program.
```
4) Update the configuration file with your chosen values. Ensure at least the repository_uri and password for both source and destination have been updated with your repository information.
5) Run restic-replica again to copy all snapshots from the source repository to the destination repository.


## Development

This project uses [uv](https://docs.astral.sh/uv) for package management.

To build the wheel and sdist:
```console
uv build
```
To run the unit test suite:
```console
uv run pytest
```