DROP TABLE IF EXISTS Journal;
DROP TABLE IF EXISTS Mood;

CREATE TABLE Journal(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "title"         TEXT DEFAULT 'New Entry',
    "entry_date"    INTEGER NOT NULL DEFAULT (date('now')),
    "mood_id"       INTEGER NOT NULL,
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES Mood(id) --This line is important to the automatic functionality of PySimpleSQL~
);
CREATE TABLE Mood(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "name"          TEXT
);
INSERT INTO Mood VALUES (1,'Happy');
INSERT INTO Mood VALUES (2,'Sad');
INSERT INTO Mood VALUES (3,'Angry');
INSERT INTO Mood VALUES (4,'Content');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (1, '2023-02-05', 1, 'Research Started!','I am excited to start my research on a large data');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (2, '2023-02-06', 2, 'Unexpected result!', 'The experiment yielded a result that was not at all what I expected.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (3, '2023-02-06', 1, 'Eureka!', 'I think I have discovered something amazing. Need to run more tests to confirm.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (4, '2023-02-07', 4, 'Serendipity', 'Sometimes the best discoveries are made by accident.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (5, '2023-02-07', 3, 'Unexpected complication', 'The experiment had an unexpected complication that may affect the validity of the results.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (6, '2023-02-07', 2, 'Need more data', 'The initial results are promising, but I need more data to confirm my hypothesis.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (7, '2023-02-08', 1, 'Feeling optimistic', 'I have a good feeling about the experiment. Will continue with the tests.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (8, '2023-02-08', 4, 'Implications for industry', 'If my discovery holds up, it could have huge implications for the industry.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (9, '2023-02-08', 3, 'Need to rethink approach', 'The initial approach did not yield the desired results. Will need to rethink my strategy.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (10, '2023-02-09', 2, 'Long way to go', 'I have a long way to go before I can confidently say that I have made a significant discovery.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (11, '2023-02-09', 1, 'Small breakthrough', 'I had a small breakthrough today. It is a step in the right direction.');
INSERT INTO Journal (id, mood_id, title, entry) VALUES (12, 4, 'I Found the Solution!', 'I can finally stop worrying about SQL syntax and focus on my research. pysimplesql is the best Python library for working with databases, and it saved me so much time and effort!');
