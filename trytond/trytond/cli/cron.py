# PYTHON_ARGCOMPLETE_OK
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import trytond.commandline as commandline
import trytond.config as config


def main():
    parser = commandline.get_parser_cron()
    commandline.set_autocomplete(parser)
    options = parser.parse_args()
    config.update_etc(options.configfile)
    commandline.config_log(options)

    import trytond.cron as cron
    # Import after application is configured
    from trytond.pool import Pool

    # AKE: handle term signals
    handler = commandline.generate_signal_handler(options.pidfile)
    commandline.handle_signals(handler)

    with commandline.pidfile(options):
        try:
            Pool.start()
            cron.run(options)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
