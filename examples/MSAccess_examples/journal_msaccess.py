import PySimpleGUI as sg
import pysimplesql as ss  # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import subprocess
import jdk
import time
import logging

# Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# -------------------------------------------------
# ROUTINES TO INSTALL JAVA IF USER DOES NOT HAVE IT
# -------------------------------------------------
def is_java_installed():
    try:
        subprocess.check_output(["which", "java"])
        return True
    except subprocess.CalledProcessError:
        return False


def progress_callback(progress_bar, current_count):
    progress_bar.update("Downloading JDK...", current_count)


def install_jdk_with_progress(jdk_version):
    jdk.get_url(jdk_version)
    progress_bar = ss.ProgressBar("Installing JDK")

    # Set cache_progress_callback attribute
    jdk.cache_progress_callback = lambda count, total: progress_callback(
        progress_bar, count
    )

    try:
        progress_bar.update("Downloading JDK...", 0)
        jdk.install(jdk_version)
        progress_bar.update("JDK installation completed.", progress_bar.max_value)
        time.sleep(
            1
        )  # Keep the progress bar visible for a short period after completion
    finally:
        progress_bar.close()


if not is_java_installed():
    res = sg.popup_yes_no(
        "Java is not installed.  Do you want to install it?", title="Java not found"
    )
    if res == "Yes":
        install_jdk(11)
    else:
        url = jdk.get_download_url(11)
        sg.popup(
            f"Java is required to run this example.  You can download it at: {url}"
        )
        exit(0)

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector using the TableHeading convenience class.
# This will also allow sorting!
headings = ss.TableHeadings(sort_enable=True)
headings.add_column("title", "Title", width=40)
headings.add_column("entry_date", "Date", width=10)
headings.add_column("mood_id", "Mood", width=20)

layout = [
    [ss.selector("Journal", sg.Table, num_rows=10, headings=headings)],
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

# Create the Window, Driver and Form
win = sg.Window("Journal example: MS Access", layout, finalize=True)
driver = ss.MSAccess("Journal.accdb")
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
        break
    elif ss.process_events(
        event, values
    ):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f"PySimpleDB event handler handled the event {event}!")
        if "edit_protect" in event:
            win["datepicker"].update(disabled=frm.get_edit_protect())
    else:
        logger.info(f"This event ({event}) is not yet handled.")
