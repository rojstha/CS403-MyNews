"""FIXTURE DATA — for automated tests only. Not live news.

Headlines and excerpts are written for testing, modelled on real events that
appeared in the live feeds on 2026-10-27. `hours_ago` is relative to the test
clock so the seven-day rules can be tested without waiting.

GROUPS: five events, each covered by 2-3 publishers -> must become 5 stories.
SEPARATE: two pairs that share a person/place but are different events.
"""

GROUPS = {
    "comey_charged": [
        ("NPR", "Trump administration moves to prosecute former FBI Director James Comey again",
         "The Justice Department is pursuing new federal charges against former FBI Director James Comey, the third attempt to prosecute him.", 5),
        ("BBC News", "Ex-FBI chief James Comey faces federal charges for third time",
         "Prosecutors have brought fresh federal charges against James Comey, the former FBI director, after two earlier cases collapsed.", 4),
        ("The Guardian", "Justice department charges ex-FBI director James Comey for third time",
         "James Comey, the former FBI director fired in 2017, has been charged by the justice department for a third time.", 3),
    ],
    "machado_return": [
        ("Fox News", "Venezuelan opposition leader María Corina Machado makes surprise return home",
         "María Corina Machado returned to Venezuela after nearly a year abroad, greeted by crowds of opposition supporters.", 10),
        ("BBC News", "Opposition leader María Corina Machado returns from exile to Venezuela",
         "Machado, the Venezuelan opposition leader, arrived in Caracas after months in exile.", 9),
        ("CBS News", "Venezuelan officials allowed Maria Corina Machado to return, Rubio says",
         "Secretary of State Marco Rubio said Venezuelan officials allowed opposition leader Maria Corina Machado to return home.", 8),
    ],
    "fairford_plot": [
        ("BBC News", "Two charged over alleged plot to assist Iran in RAF Fairford incident",
         "Two men have been charged under the National Security Act over an alleged plot linked to an incident at RAF Fairford.", 20),
        ("The Guardian", "Two men charged over alleged plot to assist Iran after RAF Fairford incident",
         "Counter-terrorism police charged two men accused of assisting Iran in connection with the RAF Fairford incident.", 19),
        ("Al Jazeera", "UK prosecutors charge two after RAF Fairford incident",
         "British prosecutors charged two men over an alleged plot to assist Iran following an incident at the RAF Fairford air base.", 18),
    ],
    "jayz_superbowl": [
        ("NPR", "Jay-Z picks himself to headline the Super Bowl halftime show",
         "Jay-Z, whose Roc Nation produces the NFL halftime show, will headline the Super Bowl in Southern California.", 30),
        ("BBC News", "Jay-Z to perform at Super Bowl half-time show",
         "The rapper Jay-Z will perform at the next Super Bowl halftime show, the NFL announced.", 29),
        ("CBS News", "Jay-Z to headline 2027 Super Bowl halftime show",
         "The NFL and Apple Music announced Jay-Z as the headliner of the Super Bowl halftime show at SoFi Stadium.", 28),
    ],
    "brewers_rays": [
        ("NPR", "Brewers rout the Rays 10-1 to move within a win of first World Series title",
         "The Milwaukee Brewers beat the Tampa Bay Rays 10-1 in Game 3 and need one more win for the World Series title.", 40),
        ("The Guardian", "Ruthless Brewers close in on World Series sweep after crushing Rays 10-1",
         "Milwaukee crushed Tampa Bay 10-1 in Game 3 of the World Series and can complete a sweep on Wednesday night.", 39),
    ],
}

SEPARATE = {
    # Same person (James Comey), different event from GROUPS["comey_charged"].
    "comey_daughter": [
        ("Fox News", "Judge rules Trump DOJ illegally fired James Comey's daughter",
         "A federal judge ruled the Justice Department illegally fired Maurene Comey, a prosecutor and daughter of James Comey.", 6),
        ("NPR", "Judge says DOJ illegally fired the daughter of former FBI director Comey",
         "Maurene Comey's firing as a federal prosecutor was unlawful, a judge ruled, ordering her reinstatement.", 6),
    ],
    # Same country (Israel), two different events.
    "israel_election": [
        ("CBS News", "Netanyahu faces first national election since Oct. 7",
         "Israelis vote in a national election seen as a referendum on Prime Minister Benjamin Netanyahu after the Gaza war.", 12),
        ("PBS NewsHour", "Netanyahu faces Israeli voters in first election since Gaza war",
         "Benjamin Netanyahu's coalition faces voters in Israel's first national election since the Gaza war began.", 11),
    ],
    "israel_westbank_mps": [
        ("BBC News", "MPs detained by Israel and barred from entering West Bank",
         "Israel detained a delegation of British MPs and barred them from entering the occupied West Bank.", 12),
        ("The Guardian", "British politicians among delegates barred from entering West Bank",
         "Israeli authorities barred international delegates including British politicians from entering the West Bank.", 11),
    ],
}

SINGLE = [
    ("PBS NewsHour", "Museum opens local history exhibit in Ohio river town",
     "A small museum opened an exhibit on the history of river trade.", 2),
]
