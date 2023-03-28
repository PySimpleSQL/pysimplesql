# ruff: noqa: F821

# Set the null value default for INTEGERS to 10;
# When reading from the database, if an INTEGER is Null, this value will be set
frm["Journal"].column_info.set_null_default("INTEGER", 10)

# Provide a complete custom set of null defaults:
# note: All supported keys must be included
null_defaults = {
    "TEXT": "New Record",
    "VARCHAR": "New Record",
    "CHAR": "New Record",
    "INTEGER": 10,
    "REAL": 100.0,
    "DOUBLE": 90.0,
    "FLOAT": 80.0,
    "DECIMAL": 70.0,
    "BOOLEAN": 1,
    "TIME": lambda x: datetime.now().strftime("%H:%M:%S"),
    "DATE": lambda x: date.today().strftime("%Y-%m-%d"),
    "TIMESTAMP": lambda x: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "DATETIME": lambda x: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}
frm["Journal"].column_info.set_null_defaults(null_defaults)
