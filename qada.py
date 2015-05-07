from __future__ import division

import os
import datetime
import contextlib

import click
import sqlalchemy as sa

config = dict()
config['QADA_PER_DAY'] = 2
config['PRAYER_NAMES'] = ('subh', 'dhuhr', '`asr', 'maghrib', 'ishaa\'')

metadata = sa.MetaData()

prayer = sa.Table(
    'prayer', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('prayer', sa.Integer, sa.CheckConstraint('prayer<=5')),
    sa.Column('date', sa.DateTime),
)


@click.group()
@click.pass_context
def cli(ctx):
    home = os.path.expanduser('~')
    db_name = '.qada.sqlite'
    db = 'sqlite:///' + os.path.join(home, db_name)
    engine = sa.create_engine(db)
    ctx.obj = engine

    if not os.path.exists(os.path.join(home, db_name)):
        db = 'sqlite:///' + os.path.join(home, db_name)
        metadata.create_all(engine)


@cli.command()
@click.option('--count', '-c',
              default=config.get('QADA_PER_DAY', 2),
              help='Number of prayers made up')
@click.pass_obj
def add(engine, count):
    with connection(engine) as conn:
        last = get_last(conn)
        prayers = [(i+1+last) % 5 or 5 for i in xrange(count)]
        click.echo('Will insert %s.' % ', '.join(get_prayer_names(prayers)))
        if click.confirm('Is this correct?'):
            values = [{'prayer': p, 'date': datetime.datetime.utcnow()}
                      for p in prayers]
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
    # the prayers in the database are ranged 1 to 5. While tuple index access
    # is from 0. So we we don't have to increment the index here.
    next_ = config['PRAYER_NAMES'][last % 5]
    click.echo(next_)


@contextlib.contextmanager
def connection(engine):
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def get_last(conn):
    stmt = sa.sql.select(
        [prayer.c.prayer]
    ).order_by(
        prayer.c.date.desc()
    ).order_by(
        prayer.c.prayer)

    try:
        return conn.execute(stmt).first()[0]
    except TypeError:
        return 0


def get_prayer_names(prayers):
    '''Maps prayer integer identifiers to their names'''
    return map(lambda i: config['PRAYER_NAMES'][i-1], prayers)
