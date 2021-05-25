CREATE TABLE Journal(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "entry_date"    INTEGER DEFAULT (date('now')),
    "mood_id"       INTEGER,
    "title"         TEXT DEFAULT "New Entry",
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES Mood(id) --This line is important to the automatic functionality of pysimplesql~
);
CREATE TABLE Mood(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "name"          TEXT
);

-- Lets pre-populate some moods into our database
-- The list doesn't need to be overdone, as the user will be able to add their own too!
INSERT INTO Mood VALUES (1,"Happy");
INSERT INTO Mood VALUES (2,"Sad");
INSERT INTO Mood VALUES (3,"Angry");
INSERT INTO Mood VALUES (4,"Emotional");
INSERT INTO Mood VALUES (5,"Content");
INSERT INTO Mood VALUES (6,"Curious");