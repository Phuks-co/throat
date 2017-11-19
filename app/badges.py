""" Here we store badges. """


badges = {  # "intname": {"name": "foo", "alt": "a badge for foo", "icon": "bar.svg", "score": 2}
    "admin": {"name": 'Admin', "alt": 'The guys that take all the blame', 'icon': 'skull.svg', 'score': 700},
    "bugger": {"name": 'Bug squasher', "alt": "Helped find or fix a bug", 'icon': 'bug.svg', 'score': 500},
    "eadop": {"name": 'Early adopter', "alt": 'You knew what you were getting into when you let me get into you', 'icon': 'trophy.svg', 'score': 500},
    "donor": {"name": 'Donor', "alt": 'Gave bucks to Phuks', "icon": 'donor.svg', 'score': 500},
    "splaw": {"name": 'Space Lawyer', "alt": '', 'icon': 'copyright.svg', 'score': 100},
    "hitler": {"name": "Literally Hitler", "alt": '', 'icon': 'evil.svg', 'score': 100},

    "miner": {"name": "Grinder", "alt": "Mined a lot of Phuks", 'icon': 'shovel.svg', 'score': 300},
    "spotlight": {"name": "Spotlight", "alt": "Top post of the day", 'icon': 'bubbles.svg', 'score': 200},
    "commando": {"name": "Keyboard commando", "alt": "Make a good post every day for a week", 'icon': 'coffee.svg', 'score': 300}
}


for bg in badges:
    try:
        badges[bg]['icon'] = open('./app/static/svg/' + badges[bg]['icon']).read()
    except FileNotFoundError:
        pass
