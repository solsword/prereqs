# TODO: Update this!
# Note: This represents different semesters to search in as a cascading
# fallback if we can't find a class description. We'll grab and merge
# info from all current semesters (last in list takes priority) and only
# if we don't find any will we start consulting previous semesters
# in-order.

# Treat semesters for current year specially to find term/instructor info
CURRENT_SEMESTERS = [
    # "202302", # Spring 2023
    "202209", # Fall 2022
]

# Past semesters to consider
PREVIOUS_SEMESTERS = [
    "202202", # Spring 2022
    "202109", # Fall 2021
    "202102", # Spring 2021
    "202009", # Fall 2020
    "202002", # Spring 2020
    "201909", # Fall 2019
]


# What to put in the h1 at the top of the page
TITLE = "CS Course Dependencies 2022-2023"
