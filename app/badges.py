""" Here we store badges. """
from flask_babel import lazy_gettext as _l

badges = {  # "intname": {"nick": "intname", "name": "foo", "alt": "a badge for foo", "icon": "bar.svg", "score": 2}
    "admin": {"nick": "admin", "name": "Admin", "alt": _l("The guys that take all the blame"), "icon": "skull.svg", "score": 700},
    "bugger": {"nick": "bugger", "name": "Bug squasher", "alt": _l("Helped find or fix a bug"), "icon": "bug.svg", "score": 500},
    "eadop": {"nick": "eadop", "name": "Early adopter", "alt": _l("You knew what you were getting into when you let me get into you"), "icon": "trophy.svg", "score": 500},
    "donor": {"nick": "donor", "name": "Donor", "alt": _l("Gave bucks to Phuks"), "icon": "donor.svg", "score": 500},
    "splaw": {"nick": "splaw", "name": "Space Lawyer", "alt": "", "icon": "copyright.svg", "score": 100},
    "hitler": {"nick": "hitler", "name": "Literally Hitler", "alt": "", "icon": "evil.svg", "score": 100},

    "miner": {"nick": "miner", "name": "Grinder", "alt": _l("Mined a lot of Phuks"), "icon": "shovel.svg", "score": 300},
    "spotlight": {"nick": "spotlight", "name": "Spotlight", "alt": _l("Top post of the day"), "icon": "bubbles.svg", "score": 200},
    "commando": {"nick": "commando", "name": "Keyboard commando", "alt": _l("Make a good post every day for a week"), "icon": "coffee.svg", "score": 300},

    "enthusiasm": {"nick": "enthusiasm", "name": "Enthusiasm", "alt": _l("Too hyped to wait!"), "icon": "account-switch.svg", "score": -100},

    "broccoli": {"nick": "broccoli", "name": "Broccoli supporter", "alt": _l("Once proud men, the Broccoli People now must remain in hiding after early on the Vegetable Wars against the Cabbages."), "icon": "broccoli.svg", "score": 100},
    "cabbage": {"nick": "cabbage", "name": "Cabbage supporter", "alt": _l("The Cabbage People are now the dominant force in the Vegetable Wars, being in the road to become an hegemon after defeating the Broccolis."), "icon": "cabbage.svg", "score": 100},

    "shitposter2018": {"nick": "2018shit", "name": "Shitposter of the year", "alt": _l("Winner of the shitposter of the year 2018 contest"), "icon": "shitposter18.svg", "score": 250}

}

for bg in badges:
    try:
        badges[bg]['icon'] = open('./app/static/svg/' + badges[bg]['icon']).read()
    except FileNotFoundError:
        pass
