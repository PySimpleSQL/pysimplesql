# Set the null value default for 'int' to 10;
# When reading from the database, if an INTEGER is Null, this value will be set
frm["Journal"].column_info.set_null_default("int", 10)

# Provide a complete custom set of null defaults:
# note: All supported keys must be included
null_defaults = {
    "str": lang.description_column_str_null_default,
    "int": 10,
    "float": 90.0,
    "Decimal": Decimal("70.0"),
    "bool": 1,
    "time": lambda: dt.datetime.now().strftime(TIME_FORMAT),
    "date": lambda: dt.date.today().strftime(DATE_FORMAT),
    "datetime": lambda: dt.datetime.now().strftime(DATETIME_FORMAT),
}
frm["Journal"].column_info.set_null_defaults(null_defaults)
