from __future__ import division

import os
import datetime
import contextlib
import ConfigParser

import click
import sqlalchemy as sa

metadata = sa.MetaData()

prayer = sa.Table(
    'prayer', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('prayer', sa.Integer, sa.CheckConstraint('prayer<=5')),
    sa.Column('date', sa.DateTime, default=datetime.datetime.utcnow),
)

cfg_path = os.path.join(os.path.expanduser('~'), '.qadarc')
if not os.path.exists(cfg_path):
    config = ConfigParser.RawConfigParser()
    config.add_section('qada')
    config.set('qada', 'qada_per_day', '2')
    config.set('qada', 'prayer_names', "subh, dhuhr, `asr, maghrib, ishaa")
    config.set('qada', 'db', '.qada.sqlite')

    with open(cfg_path, 'wb') as cfg:
        config.write(cfg)
    config.read(cfg_path)
else:
    config = ConfigParser.ConfigParser()
    config.read(cfg_path)


@click.group()
@click.pass_context
def cli(ctx):
    db_path = os.path.join(os.path.expanduser('~'),
                           config.get('qada', 'db', '.qada.sqlite'))
    db = 'sqlite:///' + db_path
    engine = sa.create_engine(db)

    if not os.path.exists(db_path):
        metadata.create_all(engine)

    ctx.obj = engine


@cli.command()
@click.option('--count', '-c',
              default=config.get('qada', 'qada_per_day', 2),
              help='Number of prayers made up.')
@click.pass_obj
def add(engine, count):
    with connection(engine) as conn:
        last = get_last(conn)
        prayers = [(i + 1 + last) % 5 or 5 for i in xrange(int(count))]
        prayer_names = config.get(
            'qada', 'prayer_names',
            'subh, dhuhr, `asr, maghrib, ishaa').split(',')
        mapped_prayer_names = map(lambda i: prayer_names[i-1], prayers)
        click.echo('Will insert %s.' % ', '.join(mapped_prayer_names))
        if click.confirm('Is this correct?'):
            values = [{'prayer': p} for p in prayers]
            conn.execute(prayer.insert(), values)


@cli.command()
@click.pass_obj
def report(engine):
    with connection(engine) as conn:
        stmt = sa.sql.select([sa.func.count(prayer.c.id).label('num_prayers')])
        result = conn.execute(stmt).first()[0]

    days = result // 5
    remaining = result % 5
    output = 'You have made up: '
    if days:
        output += '%s days, ' % days
    if remaining:
        output += '%d prayers.' % remaining
    click.echo(output)


@cli.command()
@click.pass_obj
def next(engine):
    with connection(engine) as conn:
        last = get_last(conn)
    prayer_names = config.get('qada', 'prayer_names',
                              'subh, dhuhr, `asr, maghrib, ishaa').split(',')
    next_ = prayer_names[last % 5]
    click.echo(next_)


@contextlib.contextmanager
def connection(engine):
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def get_last(conn):
    stmt = sa.sql.select([prayer.c.prayer]).order_by(prayer.c.date.desc(),
                                                     prayer.c.prayer)
    result = conn.execute(stmt).first()
    try:
        return result[0]
    except TypeError:
        return 0
