# restic-replica
The current project status should be considered as "beta".

## Info
A command line tool to copy snapshots between Restic repositories, written in python.  
What is Restic? An awesome [backup tool](https://restic.readthedocs.io/).  
Why? 
* Restic does not natively support configuration files.  
* Restic does not have a way to filter which snapshots should be copied.  

## Installation

```console
pip install restic_replica
```

## Usage

1) [Initialize](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html) both the source and destination repositories using Restic, if they have not been already initialized.   
Note: Make sure to use `--copy-chunker-params` when [initializing the destination repository](https://restic.readthedocs.io/en/stable/045_working_with_repos.html#ensuring-deduplication-for-copied-snapshots).
2) Make sure at least one [backup](https://restic.readthedocs.io/en/stable/040_backup.html) has been stored in the source repository.
3) Run `restic-replica` once to generate an empty configuration file.
```console
❯ restic-replica
ERROR: Missing configuration file
An example configuration file has been created at /home/user/.restic-replica/config.toml. Update the configuration in this file to match your system, and then re-run this program.
```
4) Update the configuration file with the correct values for your repositories. Ensure the repository_uri, a password option, and any necessary environment variables have been updated for both source and destination.
5) Optional: run `restic-replica` with the `--dry-run` flag to check the connection to both repositories, and verify the list of snapshots to be copied is as expected.
6) Run `restic-replica` again to copy snapshots from the source repository to the destination repository.


## Policy

`restic-replica` supports defining a policy within the configuration file, to filter which snapshots will be copied between the source and destination repositories.  
The filters defined in the policy work the same as the filters used with `restic forget`, in that all of the calendar-based filters (e.g. keep-daily, keep-weekly, etc.) work on natural time boundaries, and are not relative to when `restic-replica` is run.   
Weeks span from Monday 00:00 to Sunday 23:59, days from 00:00 to 23:59, etc. The _most recent_ snapshot within a calendar period is always selected.  
For example; if multiple snapshots exist on a given day, and a keep-daily filter selects a snapshot from that day, the most recent snapshot taken on that day is selected.  

Use of the `--dry-run` option is recommended to verify that the specified filter options match expectations.  

__Note:__ If no policy is set, i.e. all filter options (e.g, keep-last, keep-daily, etc.) in the configuration file are commented out, all snapshots present in the source repository will be copied to the destination repository.

### The "exclude-current-period" option

This option provides a workaround to an issue, where running `restic-replica` multiple times in the same calendar period can lead to inconsistent snapshot selection when using calendar based filters. This happens because the most recent snapshot from the calendar period is always selected, and which snapshot this is can change.

An example showing the problem:
- A new `restic` snapshot is taken daily, and backed up to a repository
- The goal is to copy all the monthly snapshots from this source repository to another, destination repository
- To accomplish this, a keep-monthly filter is applied. One snapshot from each month will be selected for copying, including the current month. 
    - The snapshot selected from the current month will be the most recent snapshot taken when `restic-replica` is run. 
    - As the source takes a new snapshot each day, the snapshot selected will be the snapshot taken on the day `restic-replica` is run.
- If `restic-replica` is run for a second time, more than a day later but still within the same calendar month, it will again select the most recent snapshot as the snapshot for the current month. 
- However, time has passed, and there is now a more recent daily snapshot in the source repository. During the second run, it is this snapshot that will be selected for copying from the current month, not the snapshot that was selected during the previous run.
- The result of this is that two snapshots for the current month will be copied to the destination repository.
- If this pattern repeats, the number of snapshots copied to the destination repository from the "current month" will continually increase. This is not ideal, as the original goal was to copy only a single snapshot from each month.

Setting the `exclude-current-period` option to true allows us to work around this problem.  
When enabled, snapshots from the "current calendar period" are excluded from any enabled calendar-based filters (e.g. keep-daily, keep-weekly, etc.), i.e. they are ignored.  

__Note:__ "current calendar period" is defined with respect to each calendar-based filter individually. For keep-daily it would be the current day, for keep-weekly the current week, etc.

Using the example above; when the keep-monthly filter is applied and exclude-current-period is enabled, any snapshots taken during the current month are treated as though they do not exist. e.g. if `restic-replica` is run on the 25th, any snapshots taken on the 1st through 25th are ignored by the keep-monthly filter, and will not be selected for copying.  

This avoids the problem, but comes with a tradeoff, in that the destination repository can be up to one calendar period "out of date" when compared to the source. The further through the calendar period, the larger the potential difference is between the data stored on the source and destination repositories.  

__Note:__ this option has no effect on keep-last.  


#### Multiple calendar based filters and "exclude-current-period"

When the exclude-current-period option is enabled, it applies to all enabled calendar-based filters (e.g. keep-daily, keep-weekly, etc.).  
However, the exclusion period is applied individually to each enabled filter.  

For example:
* If both keep-monthly and keep-daily filters are enabled, the keep-monthly filter will ignore any snapshots from the current month.
* The keep-daily filter will only ignore snapshots taken today. It will still consider including snapshots taken on the other days in the current month for copying.  


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