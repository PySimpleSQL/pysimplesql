import PySimpleGUI as sg
import pysimplesql as ss

sql="""
CREATE TABLE "Enabled"(
    "pk" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
);

CREATE TABLE "Disabled"(
    "pk
);

CREATE TABLE "Product"(
    "pk" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "fk" INTEGER NOT NULL,
    "type" INTEGER,
    "name" TEXT    
);


"""
