from __future__ import division

import os
import datetime

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

    if not os.path.exists(os.path.join(home, db_name)):
        metadata.create_all(engine)

    conn = engine.connect()
    ctx.obj = conn


@cli.command()
@click.option('--count', '-c',
              default=config.get('QADA_PER_DAY', 2),
              help='Number of prayers made up')
@click.pass_obj
def add(conn, count):
    last = get_last(conn)
    prayers = [(i+1+last) % 5 or 5 for i in xrange(count)]
    click.echo('Will insert %s.' % ', '.join(get_prayer_names(prayers)))
    if click.confirm('Is this correct?'):
        values = [{'prayer': p, 'date': datetime.datetime.utcnow()}
                  for p in prayers]
        conn.execute(prayer.insert(), values)
    conn.close()


@cli.command()
@click.pass_obj
def report(conn):
    stmt = sa.sql.select([sa.func.count(prayer.c.id).label('num_prayers')])
    result = conn.execute(stmt).first()[0]
    days = result // 5
    remaining = result % 5
    output = 'You have made up:\n'
    if days:
        output += '%s days\n' % days
    if remaining:
        output += '%d prayers' % remaining
    click.echo(output)
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
    return map(lambda i: config['PRAYER_NAMES'][i-1], prayers)
