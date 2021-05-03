

# TODO: Update this!
# Note: This represents different semesters to search in as a cascading
# fallback if we can't find a class description. We'll grab and merge
# info from all current semesters (last in list takes priority) and only
# if we don't find any will we start consulting previous semesters
# in-order.

CURRENT_SEMESTERS = [ # Treat semesters for current year specially to find term/instructor info
    "202202", # Spring 2022
    "202109", # Fall 2021
]

PREVIOUS_SEMESTERS = [ # Treat semesters for current year specially to find term/instructor info
    "202102", # Spring 2021
    "202009", # Fall 2020
    "202002", # Spring 2020
    "201909", # Fall 2019
]


# What to put in the h1 at the top of the page
TITLE = "CS Course Dependencies 2021-2022"
