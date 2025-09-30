import sys

from restic_replica import __version__, app, console


def main(argv=sys.argv[1:]):
    args = console.parse_cli_args(argv)
    config_file = app.ensure_config_file()
    config = app.read_config_file(config_file)
    logger = console.setup_logging(logdir=app.get_logdir(config))
    console.logging_headers(__version__)
    try:
        # get restic cli
        restic_cli = app.get_restic(config["restic"], verbose=args.verbose)
        # read policy info from file
        policy = app.get_policy(config["policy"])
        # instance source and target repositories
        source = app.get_repository("source", config["source"], restic_cli)
        destination = app.get_repository("target", config["destination"], restic_cli)
        # check access, then trigger copy
        logger.info("Checking access to source repository")
        app.check_repository_access(source)
        logger.info("Checking access to destination repository")
        app.check_repository_access(destination)
        logger.info("Starting copy of snapshots from source to destination repository")
        # I guess this is the logical place to add the filter.
        result = app.copy_snapshots(source, destination, policy)
        if not result.stdout:
            logger.info(
                "All snapshots from the source are already present in the destination repository"
            )
        else:
            logger.info("Finished copying snapshots")
    except RuntimeError as err:
        logger.error(err)
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
