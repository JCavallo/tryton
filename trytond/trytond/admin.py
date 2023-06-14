# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
import os
import random
import sys
from getpass import getpass

from sql import Literal, Table

from trytond import __series__, backend
from trytond.config import config
from trytond.pool import Pool
from trytond.sendmail import send_test_email
from trytond.tools import file_open, find_path
from trytond.tools.email_ import EmailNotValidError, validate_email
from trytond.transaction import Transaction, TransactionError, inactive_records

from trytond.modules import get_module_info

__all__ = ['run']
logger = logging.getLogger(__name__)


# XUNG
def _init_upgrade_version_control_table(db_name):
    with Transaction().start(db_name, 0) as transaction:
        cursor = transaction.connection.cursor()
        cursor.execute(
            "SELECT EXISTS("
            "SELECT * FROM information_schema.tables "
            "WHERE table_name='upgrade_version_control')")

        if not cursor.fetchone()[0]:
            sql_file = os.path.join(os.path.dirname(__file__),
                'backend/postgresql/init_upgrade_version_control.sql')
            with open(sql_file) as fp:
                for line in fp.read().split(';'):
                    if (len(line) > 0) and (not line.isspace()):
                        cursor.execute(line)


def _check_update_needed(db_name, options):
    # Get current main module version
    main_module = config.get('version', 'module', default='coog_core')
    current_main_module_version = get_module_info(main_module)['version']

    # Do the upgrade anyway if -u is activated
    if options.update:
        return True, current_main_module_version

    # Get main module version which stocked in the database
    version_control_table = Table('upgrade_version_control')
    cursor = Transaction().connection.cursor()
    cursor.execute(
        *version_control_table.select(version_control_table.current_version))
    db_main_module_version = cursor.fetchone()[0]

    if (options.check_update and current_main_module_version !=
            db_main_module_version):
        logger.warning(
            f'Current code version ({current_main_module_version}) is '
            'different from the last update version '
            f'({db_main_module_version}), updating')
        return True, current_main_module_version

    logger.warning(
        f'Current code version ({current_main_module_version}) '
        'matches last update version, nothing to do')
    return False, current_main_module_version


def _init_pool(db_name, options, lang):
    pool = Pool(db_name)

    with Transaction().start(db_name, 0) as transaction:
        try:
            if options.check_update:
                # This lock of table will block others workers /
                # processes until the current upgrade is finished
                # Attention: lock activated only when -cu is activated
                # -u can do the update normally
                cursor = transaction.connection.cursor()
                cursor.execute(
                    "LOCK upgrade_version_control IN EXCLUSIVE MODE")

            upgrade_needed, new_version = _check_update_needed(
                db_name, options)
            if not upgrade_needed:
                options.update, options.check_update = [], []
            updated_needed = options.update or options.check_update

            pool.init(
                update=updated_needed, lang=list(lang),
                activatedeps=options.activatedeps,
                indexes=options.indexes)

            if updated_needed:
                # If upgrade finishes correctly->update version in database
                version_control_table = Table('upgrade_version_control')
                cursor = transaction.connection.cursor()
                cursor.execute(*version_control_table.update(
                    columns=[version_control_table.current_version],
                    values=[new_version]))
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
    return pool


def run(options):
    main_lang = config.get('database', 'language')
    init = {}

    if options.test_email:
        send_test_email(options.test_email)

    for db_name in options.database_names:
        init[db_name] = False
        database = backend.Database(db_name)
        database.connect()
        if options.update or options.check_update:
            if not database.test():
                logger.info("init db")
                database.init()
                init[db_name] = True
        elif not database.test():
            raise Exception('"%s" is not a Tryton database.' % db_name)

    for db_name in options.database_names:
        if options.update or options.check_update:
            with Transaction().start(db_name, 0) as transaction,\
                    transaction.connection.cursor() as cursor:
                database = backend.Database(db_name)
                database.connect()
                if not database.test():
                    raise Exception('"%s" is not a Tryton database.' % db_name)
                lang = Table('ir_lang')
                cursor.execute(*lang.select(lang.code,
                        where=lang.translatable == Literal(True)))
                lang = set([x[0] for x in cursor])
            lang.add(main_lang)
        else:
            lang = set()

        lang |= set(options.languages)

        # XUNG
        # Create upgrade version control table if it doesn't exist
        _init_upgrade_version_control_table(db_name)

        pool = _init_pool(db_name, options, lang)

        if options.update_modules_list:
            with Transaction().start(db_name, 0) as transaction:
                Module = pool.get('ir.module')
                Module.update_list()

        if lang:
            with Transaction().start(db_name, 0) as transaction:
                pool = Pool()
                Lang = pool.get('ir.lang')
                languages = Lang.search([
                        ('code', 'in', lang),
                        ])
                Lang.write(languages, {
                        'translatable': True,
                        })

    for db_name in options.database_names:
        if options.email is not None:
            email = options.email
        elif init[db_name]:
            while True:
                email = input(
                    '"admin" email for "%s" (empty for none): ' % db_name)
                if email:
                    try:
                        validate_email(email)
                    except EmailNotValidError as e:
                        sys.stderr.write(str(e) + '\n')
                        continue
                break
        else:
            email = None

        password = ''
        if init[db_name] or options.password:
            # try to read password from environment variable
            # TRYTONPASSFILE, empty TRYTONPASSFILE ignored
            passpath = os.getenv('TRYTONPASSFILE')
            if passpath:
                try:
                    with open(passpath) as passfile:
                        password, = passfile.read().splitlines()
                except Exception as err:
                    sys.stderr.write('Can not read password '
                        'from "%s": "%s"\n' % (passpath, err))

            if not password and not options.reset_password:
                while True:
                    password = getpass(
                        f'"{options.login}" password for "{db_name}": ')
                    password2 = getpass(
                        f'"{options.login}" password confirmation: ')
                    if password != password2:
                        sys.stderr.write(
                            f'"{options.login}" password confirmation '
                            f'doesn\'t match "{options.login}" password.\n')
                        continue
                    if not password:
                        sys.stderr.write(
                            f'"{options.login}" password is required.\n')
                        continue
                    break

        transaction_extras = {}
        while True:
            with Transaction().start(
                    db_name, 0, **transaction_extras) as transaction:
                try:
                    pool = Pool()
                    User = pool.get('res.user')
                    Configuration = pool.get('ir.configuration')
                    configuration = Configuration(1)
                    if init[db_name]:
                        configuration.series = __series__

                    with inactive_records():
                        users = User.search([('login', '=', options.login)])
                        if not users:
                            sys.stderr.write(
                                f'User with login "{options.login}"'
                                ' not found.\n')
                            break
                        user, = users

                        if not user.active:
                            activate = input(
                                f'Warning: User "{options.login}" is '
                                'inactive. Proceeding will activate the user. '
                                'Continue? (Y/n): ').strip().lower() or 'y'
                            if activate == 'y':
                                user.active = True
                                sys.stderr.write(
                                    f'User "{options.login}" activated.\n')
                            else:
                                sys.stderr.write('Activation cancelled\n')

                    if email is not None:
                        user.email = email
                    if init[db_name] or options.password:
                        configuration.language = main_lang
                        if not options.reset_password:
                            user.password = password
                    user.save()
                    if options.reset_password:
                        User.reset_password([user])
                    if options.hostname is not None:
                        configuration.hostname = options.hostname or None
                    if options.export_translations:
                        Lang = pool.get('ir.lang')
                        Translation = pool.get('ir.translation')
                        TranslationSet = pool.get(
                            'ir.translation.set', type='wizard')
                        TranslationClean = pool.get(
                            'ir.translation.clean', type='wizard')
                        TranslationUpdate = pool.get(
                            'ir.translation.update', type='wizard')

                        logger.info("set translations")
                        session_id, _, _ = TranslationSet.create()
                        TranslationSet.execute(session_id, {}, 'set_')
                        TranslationSet.delete(session_id)

                        logger.info("clean translations")
                        session_id, _, _ = TranslationClean.create()
                        TranslationClean.execute(session_id, {}, 'clean')
                        TranslationClean.delete(session_id)

                        for language in options.languages:
                            logger.info(
                                "synchronize translations %s", language)
                            language, = Lang.search([
                                    ('code', '=', language),
                                    ])

                            session_id, _, _ = TranslationUpdate.create()
                            TranslationUpdate.execute(session_id, {
                                    'start': {
                                        'language': language.id,
                                        },
                                    }, 'update')
                            TranslationUpdate.delete(session_id)

                        for module in options.update:
                            for language in options.languages:
                                logger.info(
                                    "export %s translations %s",
                                    module, language)
                                filename = os.path.join(
                                    module, 'locale', f'{language}.po')
                                pofile = Translation.translation_export(
                                    language, module)
                                if pofile is not None:
                                    with file_open(filename, 'wb') as fp:
                                        fp.write(pofile)
                                else:
                                    try:
                                        os.remove(find_path(filename))
                                    except FileNotFoundError:
                                        pass

                    configuration.save()
                except TransactionError as e:
                    transaction.rollback()
                    e.fix(transaction_extras)
                    continue
                break
        with Transaction().start(db_name, 0, readonly=True):
            if options.validate is not None:
                validate(options.validate, options.validate_percentage)


def validate(models, percentage=100):
    from trytond.model import ModelSingleton, ModelStorage
    from trytond.model.exceptions import ValidationError
    logger = logging.getLogger('validate')
    pool = Pool()
    if not models:
        models = sorted([n for n, _ in pool.iterobject()])
    ratio = min(100, percentage) / 100
    in_max = Transaction().database.IN_MAX
    for name in models:
        logger.info("validate: %s", name)
        Model = pool.get(name)
        if not issubclass(Model, ModelStorage):
            continue
        offset = 0
        limit = in_max
        while True:
            records = Model.search(
                [], order=[('id', 'ASC')], offset=offset, limit=limit)
            if not records:
                break
            records = Model.browse(
                random.sample(records, int(len(records) * ratio)))
            try:
                for record in records:
                    try:
                        Model._validate([record])
                    except ValidationError as exception:
                        logger.error("%s: KO '%s'", record, exception)
                    else:
                        logger.info("%s: OK", record)
            except TransactionError:
                logger.info("%s: SKIPPED", name)
                break
            if issubclass(Model, ModelSingleton):
                break
            offset += limit
