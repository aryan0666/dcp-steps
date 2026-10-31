# Data Centric Programming Assignment 2026: My Daily Steps

# Description of the project
I am tracking how much I walk each day and how it relates to my routine and energy.
Every night at the same time I read my step count from my phone's step counter and
record it by hand, along with a few details about my day. Over the semester I will
build a Python application that loads this data into a SQLite database, analyses it
with pandas, and lets a user explore it.

Data collection started on 30 October 2026. The data is in [data/steps.csv](data/steps.csv).

# Questions
1. Do I walk more on college days than on days off?
2. Am I more energetic on days when I walk more?
3. Does the weather change how much I walk or how long I spend outside?

# Data Dictionary

| Column | Type | Units / values | How I measure it |
|---|---|---|---|
| date | date | YYYY-MM-DD | The date the row is recorded |
| time_recorded | time | HH:MM (24h) | The time I read my step count each night |
| steps | integer | steps | Read from my phone's step counter at the end of the day |
| college_day | categorical | y / n | Whether I attended college that day |
| transport | categorical | walk / bus / luas / car / none | The main way I travelled that day |
| minutes_outside | integer | minutes | Time spent outdoors that day, written down on the day |
| energy | integer | 1-5 (1 = exhausted, 5 = full of energy) | My own rating at the end of the day |
| weather | categorical | sunny / cloudy / rain | The main weather that day where I was |

**Rules:** I record one row per day, at roughly the same time each night, using the
same phone.


# Data collection photos
Photos of my data collection will be added here.
