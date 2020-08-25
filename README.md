# PySimpleSQL

This is just a stub readme for now, as I have to learn the markdown for these readme.md documents.  Here is some bare minimum information for now:

Use:

Import the modules:

`import PySimpleGUI as sg
import PySimpleSQL as ss`

To get the easiest experience with PySimpleSQL, the magic is in the database creation.
The automatic functionality of PySimpleSQL relies on just a couple of things:
- foreign key constraints on the database tables
- a CASCADE ON UPDATE constraint on any tables that should automatically refresh in the GUI
See sample below:
- PySimpleGUI control keys need to be named {table}.{field} for automatic mapping.  Of course, manual mapping is supported as well. ss.record() is a convenience function/"custom control" to make adding records quick and easy!


`CREATE TABLE "Book"(
    "pkBook" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT,
    "author" TEXT
);
CREATE TABLE "Chapter"(
    "pkChapter" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT,
    "fkBook" INTEGER,
    "startPage" INTEGER,
    -- SECRET SAUCE BELOW! If you have foreign key constraints set on the database,
    -- then PySimpleSQL will pick them up!
    -- note: ON UPDATE CASCADE only needed if you want automatic GUI refreshing
    -- (i.e. not every constraint needs them, like fields that will populate comboboxes for example)
    FOREIGN KEY(fkBook) REFERENCES Book(pkBook) ON UPDATE CASCADE
);`
todo: How to format the code block better?

