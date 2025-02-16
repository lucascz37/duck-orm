from databases.core import Database
from dotenv import load_dotenv
import functools
import asyncio
import pytest
import os

from duck_orm.model import Model
from duck_orm.sql import fields as Field
from duck_orm.sql.condition import Condition
from duck_orm.exceptions import UpdateException

load_dotenv()
database_url = os.getenv('DATABASE_TEST_URL')

db = Database(
    f'postgresql://{database_url}')


class MyTest(Model):
    __db__ = db

    id: int = Field.Integer(primary_key=True, auto_increment=True)
    msg: str = Field.String(not_null=True)


class Person(Model):
    __tablename__ = 'persons'
    __db__ = db

    id: int = Field.Integer(primary_key=True, auto_increment=True)
    first_name: str = Field.String(unique=True)
    last_name: str = Field.String(not_null=True)
    age: int = Field.Integer()
    salary: int = Field.BigInteger()


def async_decorator(func):
    """
    Decorator used to run async test cases.
    """

    @functools.wraps(func)
    def run_sync(*args, **kwargs):
        loop = asyncio.get_event_loop()
        task = func(*args, **kwargs)
        return loop.run_until_complete(task)

    return run_sync


def test_model_class():
    assert Person.get_name() == 'persons'
    assert MyTest.get_name() == 'mytest'
    assert isinstance(Person.first_name, Field.String)
    assert issubclass(Person, Model)


def test_create_sql():
    sql = Person._Model__get_create_sql()
    assert sql == "CREATE TABLE IF NOT EXISTS persons (" + \
        "salary BIGINT, " + \
        "last_name TEXT NOT NULL, " + \
        "id SERIAL PRIMARY KEY, " + \
        "first_name TEXT UNIQUE, " + \
        "age INTEGER);"


def get_table(table, tables):
    for tup in tables:
        if (tup['tablename'] == table):
            return True
    return False


@ async_decorator
async def test_create_table():
    await db.connect()
    await Person.create()
    await MyTest.create()
    tables = await Person.find_all_tables()
    assert get_table('persons', tables)


@ async_decorator
async def test_save_person():
    t = MyTest(msg="Teste 1")
    await MyTest.save(t)
    testes = await MyTest.find_all(['msg'])
    assert testes[0].msg == 'Teste 1'


@ async_decorator
async def test_save_person():
    p = Person(first_name="Rich", last_name="Rich Ramalho",
               age=21, salary=10000000)
    await p.save(p)
    persons = await Person.find_all(['first_name'])
    assert persons[0].first_name == 'Rich'


@ async_decorator
async def test_select_all_persons():
    p = Person(first_name="Lucas", last_name="Lucas Andrade",
               age=21, salary=20000000)
    await p.save(p)
    persons = await Person.find_all()
    assert persons[0].first_name == 'Rich'
    assert persons[1].first_name == 'Lucas'


@ async_decorator
async def test_select_all_excludes_persons():
    persons = await Person.find_all(fields_excludes=['id', 'last_name', 'age'])
    assert persons[0].id is None
    assert persons[0].last_name is None
    assert persons[0].first_name == 'Rich'
    assert persons[0].age is None
    assert persons[0].salary == 10000000


@ async_decorator
async def test_sql_select_where_persons():
    sql = Person._Model__get_select_sql(
        conditions=[
            Condition('first_name', '=', 'Rich')
        ]
    )
    fields = sql[0].split('SELECT ')[1].split(' FROM ')[0]
    assert fields.__contains__('id')
    assert fields.__contains__('age')
    assert fields.__contains__('first_name')
    assert fields.__contains__('last_name')
    assert fields.__contains__('salary')
    msg = "SELECT {fields} FROM persons WHERE first_name = 'Rich';".format(
        fields=fields)
    assert sql[0] == msg


@async_decorator
async def test_select_where_persons():
    persons = await Person.find_all(
        conditions=[
            Condition('first_name', '=', 'Rich')
        ]
    )
    assert len(persons) == 1
    assert persons[0].first_name == 'Rich'


@async_decorator
async def test_select_all_limit():
    p = Person(first_name="Teste 1", last_name="First",
               age=21, salary=20000000)
    await p.save(p)
    persons = await Person.find_all(limit=2)
    assert len(persons) == 2
    assert persons[0].first_name == 'Rich'
    assert persons[1].first_name == 'Lucas'


@async_decorator
async def test_delete_person():
    await Person.delete(
        conditions=[
            Condition('first_name', '=', 'Rich')
        ]
    )
    persons = await Person.find_all()
    assert len(persons) == 2
    assert persons[0].first_name == 'Lucas'


@async_decorator
async def test_find_one():
    person = await Person.find_one(conditions=[
        Condition('first_name', '=', 'Lucas')
    ])
    assert person is not None
    assert person.first_name == 'Lucas'
    assert person.last_name == 'Lucas Andrade'


@async_decorator
async def test_find_like():
    person = await Person.find_one(conditions=[
        Condition('first_name', 'LIKE', 'LUCAS', True),
        Condition('last_name', 'LIKE', 'lUcas aNdrade', True)
    ])
    assert person.first_name == 'Lucas'
    assert person.last_name == 'Lucas Andrade'


@async_decorator
async def test_find_one_not_found():
    person = await Person.find_one(conditions=[
        Condition('first_name', '=', 'Rich')
    ])
    assert person is None


@async_decorator
async def test_update_sql():
    person = await Person.find_one(conditions=[
        Condition('first_name', '=', 'Teste 1')
    ])
    assert person.first_name == 'Teste 1'
    p = await person.update(first_name='Teste 1 UPDATE', last_name='UPDATE')
    assert p.id == 3
    assert p.first_name == 'Teste 1 UPDATE'
    assert p.last_name == 'UPDATE'


@async_decorator
async def test_update_sql_without_id():
    person = await Person.find_one(fields_excludes=['id'], conditions=[
        Condition('first_name', '=', 'Teste 1 UPDATE')
    ])
    assert person.first_name == 'Teste 1 UPDATE'
    assert person.id is None
    with pytest.raises(UpdateException):
        p = await person.update(first_name='Teste 2 UPDATE',
                                last_name='UPDATE 2')
    assert person.first_name == 'Teste 1 UPDATE'
    assert person.last_name == 'UPDATE'


@async_decorator
async def test_drop_table():
    await Person.drop_table()
    await MyTest.drop_table()
