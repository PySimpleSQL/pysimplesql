DROP TABLE IF EXISTS "Journal";
DROP TABLE IF EXISTS "Mood";

CREATE TABLE "Mood"(
    "id"            SERIAL NOT NULL PRIMARY KEY,
    "name"          TEXT
);

CREATE TABLE "Journal"(
    "id"            SERIAL NOT NULL PRIMARY KEY,
    "title"         TEXT DEFAULT 'New Entry' NOT NULL,
    "entry_date"    DATE DEFAULT CURRENT_DATE NOT NULL,
    "mood_id"       INTEGER NOT NULL,
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES "Mood"(id)
);

INSERT INTO "Mood" (name) VALUES ('Happy');
INSERT INTO "Mood" (name) VALUES ('Sad');
INSERT INTO "Mood" (name) VALUES ('Angry');
INSERT INTO "Mood" (name) VALUES ('Content');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-05 08:00:00', 1, 'Research Started!','I am excited to start my research on a large data');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-06 12:30:00', 2, 'Unexpected result!', 'The experiment yielded a result that was not at all what I expected.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-06 18:45:00', 1, 'Eureka!', 'I think I have discovered something amazing. Need to run more tests to confirm.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-07 09:15:00', 4, 'Serendipity', 'Sometimes the best discoveries are made by accident.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-07 13:30:00', 3, 'Unexpected complication', 'The experiment had an unexpected complication that may affect the validity of the results.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-07 19:00:00', 2, 'Need more data', 'The initial results are promising, but I need more data to confirm my hypothesis.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-08 11:00:00', 1, 'Feeling optimistic', 'I have a good feeling about the experiment. Will continue with the tests.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-08 16:00:00', 4, 'Implications for industry', 'If my discovery holds up, it could have huge implications for the industry.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-08 21:30:00', 3, 'Need to rethink approach', 'The initial approach did not yield the desired results. Will need to rethink my strategy.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-09 10:00:00', 2, 'Long way to go', 'I have a long way to go before I can confidently say that I have made a significant discovery.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-09 15:15:00', 1, 'Small breakthrough', 'I had a small breakthrough today. It is a step in the right direction.');
INSERT INTO "Journal" (entry_date, mood_id, title, entry) VALUES ('2023-02-09 15:15:00', 1, 'I Found the Solution!', 'I can finally stop worrying about SQL syntax and focus on my research. pysimplesql is the best Python library for working with databases, and it saved me so much time and effort!');
