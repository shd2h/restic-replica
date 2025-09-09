from restic_replica import __version__, app, console


def main():
    config_file = app.ensure_config_file()
    config = app.read_config_file(config_file)
    # TODO: read the logging path from the config file. Allow setting to none?
    logger = console.setup_logging()
    console.logging_headers(__version__)
    # get restic cli
    restic_cli = app.get_restic(config["restic"])
    # instance source and target repositories
    source = app.get_repository("source", config["source"], restic_cli)
    destination = app.get_repository("target", config["destination"], restic_cli)
    # check access, then trigger copy
    try:
        app.check_repository_access(source)
        app.check_repository_access(destination)
        app.copy_snapshots(source, destination)
    except RuntimeError as err:
        logger.error(err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
