# ruff: skip-file

import contextlib

import docker.errors
import pytest

import pysimplesql as ss
from pysimplesql.docker_utils import *  # noqa F403


# --------------------------------------------------------------------------------------
# Create session-level fixtures for the docker containers to provide database servers
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def mysql_container():
    docker_image = "pysimplesql/examples:mysql"
    docker_image_pull(docker_image)
    docker_container = docker_container_start(
        image=docker_image,
        container_name="pysimplesql-examples-mysql",
        ports={"3306/tcp": ("127.0.0.1", 3306)},
    )
    yield docker_container
    with contextlib.suppress(docker.errors.APIError):
        docker_container.stop()


@pytest.fixture(scope="session", autouse=True)
def postgres_container():
    docker_image = "pysimplesql/examples:postgres"
    docker_image_pull(docker_image)
    docker_container = docker_container_start(
        image=docker_image,
        container_name="pysimplesql-examples-postgres",
        ports={"5432/tcp": ("127.0.0.1", 5432)},
    )
    yield docker_container
    with contextlib.suppress(docker.errors.APIError):
        docker_container.stop()


@pytest.fixture(scope="session", autouse=True)
def sqlserver_container():
    docker_image = "pysimplesql/examples:sqlserver"
    docker_image_pull(docker_image)
    docker_container = docker_container_start(
        image=docker_image,
        container_name="pysimplesql-examples-sqlserver",
        ports={"1433/tcp": ("127.0.0.1", 1433)},
    )
    yield docker_container
    with contextlib.suppress(docker.errors.APIError):
        docker_container.stop()


# Credentials to use each with the docker servers
mysql_docker = {
    "user": "pysimplesql_user",
    "password": "pysimplesql",
    "host": "127.0.0.1",
    "database": "pysimplesql_examples",
}

postgres_docker = {
    "host": "localhost",
    "user": "pysimplesql_user",
    "password": "pysimplesql",
    "database": "pysimplesql_examples",
}

sqlserver_docker = {
    "host": "127.0.0.1",
    "user": "pysimplesql_user",
    "password": "Pysimplesql!",
    "database": "pysimplesql_examples",
}


# --------------------------------------------------------------------------------------
# Use a fixture to create a driver instance for each test
# --------------------------------------------------------------------------------------
@pytest.fixture(
    params=[
        ss.Driver.sqlite,
        ss.Driver.flatfile,
        ss.Driver.mysql,
        ss.Driver.postgres,
        ss.Driver.sqlserver,
        ss.Driver.msaccess,
    ]
)
def driver(request):
    driver_class = request.param

    # Use an in-memory database for sqlite tests
    if driver_class == ss.Driver.sqlite:
        return driver_class(db_path=":memory:")
    if driver_class == ss.Driver.flatfile:
        return driver_class(file_path="test.csv")
    if driver_class == ss.Driver.mysql:
        return driver_class(**mysql_docker)
    if driver_class == ss.Driver.postgres:
        return driver_class(**postgres_docker)
    if driver_class == ss.Driver.sqlserver:
        return driver_class(**sqlserver_docker)
    if driver_class == ss.Driver.msaccess:
        return driver_class(database_file="test.accdb")
    raise NotImplementedError("Driver class not supported in tests.")


# --------------------------------------------------------------------------------------
# General tests that apply to all SQLDriver implementations
# --------------------------------------------------------------------------------------
# Note: driver-specific implementations will be provided after this section


# Test creating a connection
@pytest.mark.parametrize(
    "driver",
    [
        ss.Driver.sqlite,
        ss.Driver.flatfile,
        ss.Driver.mysql,
        ss.Driver.postgres,
        ss.Driver.sqlserver,
        ss.Driver.msaccess,
    ],
    indirect=True,
)
def test_connect(driver):
    driver_class = driver.__class__

    # Note: We don't actually need to look at the driver classes in this case
    # as the action for all is exactly the same.  I just wanted a good example
    # of how we can separate logic out for individual drivers if needed.
    if driver_class == ss.Driver.sqlite:
        assert driver.con is not None
    elif driver_class == ss.Driver.flatfile:
        assert driver.con is not None  # uses sqlite, so should have con
    elif driver_class == ss.Driver.mysql:
        assert driver.con is not None
    elif driver_class == ss.Driver.postgres:
        assert driver.con is not None
    elif driver_class == ss.Driver.sqlserver:
        assert driver.con is not None
    elif driver_class == ss.Driver.msaccess:
        assert driver.con is not None
    else:
        raise NotImplementedError("Driver class not supported in tests.")


# Test closing a connection
@pytest.mark.parametrize(
    "driver",
    [
        ss.Driver.sqlite,
        ss.Driver.flatfile,
        ss.Driver.mysql,
        ss.Driver.postgres,
        ss.Driver.sqlserver,
        ss.Driver.msaccess,
    ],
    indirect=True,
)
def test_close(driver):
    # Close the driver
    driver.close()

    # Now see if we can execute a simple query.  If we can, it did not close properly
    query = "SELECT 1"

    with pytest.raises(Exception):
        driver.execute(query)


# Test creating tables
@pytest.mark.parametrize(
    "driver",
    [
        ss.Driver.sqlite,
        ss.Driver.flatfile,
        ss.Driver.mysql,
        ss.Driver.postgres,
        ss.Driver.sqlserver,
        # ss.Driver.msaccess, #MSAccess not quite working yet...
    ],
    indirect=True,
)
def test_create_table(driver: ss.SQLDriver):
    driver_class = driver.__class__
    # Create
    table = "TestAaBb123"
    table_quoted = driver.quote_table(table)

    # Drop the table so we start clean
    query = f"DROP TABLE IF EXISTS {table_quoted};"
    driver.execute(query)
    driver.commit()

    reference_tables = driver.get_tables()
    print(driver_class, "reference_tables", reference_tables)
    assert table not in reference_tables

    # Now create the table
    query = f"CREATE TABLE {table_quoted} (id INTEGER);"
    driver.execute(query)
    driver.commit()

    # Get tables again
    tables = driver.get_tables()
    print(driver_class, "tables", tables)
    assert table in tables


"""
@pytest.mark.parametrize("sql_driver_instance", [
    ss.Driver.sqlite,
    ss.Driver.flatfile,
    ss.Driver.mysql,
    ss.Driver.postgres,
    ss.Driver.sqlserver,
    ss.Driver.msaccess
], indirect=True)
def test_get_tables(sql_driver_instance):


@pytest.mark.parametrize("sql_driver_instance", [
    ss.Driver.sqlite,
    ss.Driver.flatfile,
    ss.Driver.mysql,
    ss.Driver.postgres,
    ss.Driver.sqlserver,
    ss.Driver.msaccess
], indirect=True)
def test_column_info(sql_driver_instance):


@pytest.mark.parametrize("sql_driver_instance", [
    ss.Driver.sqlite,
    ss.Driver.flatfile,
    ss.Driver.mysql,
    ss.Driver.postgres,
    ss.Driver.sqlserver,
    ss.Driver.msaccess
], indirect=True)
def test_execute_query(sql_driver_instance):


@pytest.mark.parametrize("sql_driver_instance", [
    ss.Driver.sqlite,
    ss.Driver.flatfile,
    ss.Driver.mysql,
    ss.Driver.postgres,
    ss.Driver.sqlserver,
    ss.Driver.msaccess
], indirect=True)
def test_relationships(sql_driver_instance):

"""
