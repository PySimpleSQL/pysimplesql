import PySimpleGUI as sg
import pysimplesql as ss  # <=== PySimpleSQL lines will be marked like this.  There's only a few!
from pysimplesql.docker_utils import *
import logging

# Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------------------
# MS SQLSERVER EXAMPLE USING DOCKER TO PROVIDE A POSTGRES SERVER
# Note that docker must be installed and configured properly on your local machine.
# Additionally, install the ODBC Driver for SQL Server, v17
# https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
# --------------------------------------------------------------------------------------

# Load in the docker image and create a container to run the Postgres server.
# See the Journal.sql file in the SQLServer_examples/docker folder to see the SQL
# statements that were used to create the database.
docker_image = "pysimplesql/examples:sqlserver"
docker_image_pull(docker_image)
docker_container = docker_container_start(
    image=docker_image,
    container_name="pysimplesql-examples-sqlserver",
    ports={"1433/tcp": ("127.0.0.1", 1433)},
)

# The original docker has DEFAULT for entry_date column as GETDATE()
# which returns a DateTime. We just want the date
sql_commands = """
DECLARE @ConstraintName nvarchar(200)
SELECT @ConstraintName = Name FROM SYS.DEFAULT_CONSTRAINTS
WHERE PARENT_OBJECT_ID = OBJECT_ID('Journal')
AND PARENT_COLUMN_ID = (SELECT column_id FROM sys.columns
                        WHERE NAME = N'entry_date'
                        AND object_id = OBJECT_ID(N'Journal'))
IF @ConstraintName IS NOT NULL
EXEC('ALTER TABLE Journal DROP CONSTRAINT ' + @ConstraintName);
ALTER TABLE [Journal] ADD DEFAULT CAST(GETDATE() AS DATE) FOR [entry_date];
"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector using the TableHeading convenience class.
# This will also allow sorting!
table_builder = ss.TableBuilder(num_rows=10)
table_builder.add_column("title", "Title", width=40)
table_builder.add_column("entry_date", "Date", width=10)
table_builder.add_column("mood_id", "Mood", width=20)

layout = [
    [ss.selector("Journal", table_builder)],
    [ss.actions("Journal")],
    [
        ss.field("Journal.entry_date"),
        sg.CalendarButton(
            "Select Date",
            close_when_date_chosen=True,
            target="Journal.entry_date",  # <- target matches field() name
            format="%Y-%m-%d",
            size=(10, 1),
            key="datepicker",
        ),
    ],
    [
        ss.field(
            "Journal.mood_id",
            sg.Combo,
            size=(30, 10),
            label="My mood:",
            auto_size_text=False,
        )
    ],
    [ss.field("Journal.title")],
    [ss.field("Journal.entry", sg.MLine, size=(71, 20))],
]
sqlserver_docker = {
    "host": "127.0.0.1",
    "user": "pysimplesql_user",
    "password": "Pysimplesql!",
    "database": "pysimplesql_examples",
}
# Create the Window, Driver and Form
win = sg.Window("Journal example: MS SQLServer", layout, finalize=True)
# Use the postgres examples database credentials
driver = ss.Driver.sqlserver(**sqlserver_docker, sql_commands=sql_commands)
frm = ss.Form(driver, bind_window=win)  # <=== Here is the magic!

# Reverse the default sort order so new journal entries appear at the top
frm["Journal"].set_order_clause("ORDER BY entry_date ASC")
# Set the column order for search operations.  By default, only the designated
# description column is searched
frm["Journal"].set_search_order(["entry_date", "title", "entry"])
# Requery the data since we made changes to the sort order
frm["Journal"].requery()

# ------------------------------------------
# How to Edit Protect your sg.CalendarButton
# ------------------------------------------
# By default, action() includes an edit_protect() call, that disables edits in the
# window. You can toggle it off with:
frm.edit_protect()  # Comment this out to edit protect elements on Window creation.
# Set initial CalendarButton state to the same as pysimplesql elements
win["datepicker"].update(disabled=frm.get_edit_protect())
# Then watch for the 'edit_protect' event in your Main Loop

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if event == sg.WIN_CLOSED or event == "Exit":
        # Ensure proper closing of our resources
        driver.close()
        frm.close()
        win.close()
        docker_container.stop()
        break
    elif ss.process_events(
        event, values
    ):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f"PySimpleDB event handler handled the event {event}!")
        if "edit_protect" in event:
            win["datepicker"].update(disabled=frm.get_edit_protect())
    else:
        logger.info(f"This event ({event}) is not yet handled.")
