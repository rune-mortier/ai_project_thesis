"""Moeilijke variant van de cv-tabellen: woorden, labels, formaten en formuleringen die NIET in
de regex-lijsten van regex_baseline.py staan. Elke gevoelige waarde krijgt een 'variant':
  unseen_word   woord buiten de lijsten (andere aandoening, nationaliteit, religie, ...)
  other_phrase  andere formulering, zonder het vaste zinspatroon
  other_label   ander veldlabel dan in de generator-basisset
  other_format  ander formaat (telefoon, datum, adres)
De regex is bevroren (tag regex-v1) en wordt NIET aangepast op deze set."""
from cv_data import MONTHS

HARD_LABELS = {
    "nl": dict(email="Mail", phone="GSM", address="Woonplaats", birth="Geboren", nat="Staatsburgerschap",
               marital="Burgerstaat", children="Gezin"),
    "en": dict(email="Contact email", phone="Mobile", address="Home", birth="DOB", nat="Citizenship",
               marital="Status", children="Dependants"),
}
HARD_NATIONALITY = {"nl": ["Italiaans", "Roemeens", "Spaans", "Portugees", "Congolees"],
                    "en": ["Italian", "Romanian", "Spanish", "Portuguese", "Congolese"]}
HARD_MARITAL = {"nl": ["Alleenstaand", "Wettelijk samenwonend", "Weduwe/weduwnaar"],
                "en": ["Widowed", "In a civil partnership", "Separated"]}
HARD_CONDITIONS = {"nl": ["epilepsie", "ADHD", "multiple sclerose", "een hartritmestoornis"],
                   "en": ["epilepsy", "ADHD", "multiple sclerosis", "a heart condition"]}
HARD_HEALTH = {"nl": ["Wegens {c} was ik in 2021 drie maanden afwezig.", "Ik heb {c} en werk daarom bij voorkeur overdag."],
               "en": ["Because of {c} I was absent for three months in 2021.", "I live with {c} and therefore prefer daytime work."]}
HARD_RELIGION = {"nl": ["Vrijwilliger bij de Boeddhistische Gemeenschap van {city}", "Lid van de Joodse Gemeenschap {city}"],
                 "en": ["Volunteer at the {city} Buddhist Community", "Member of the {city} Jewish Community"]}
HARD_UNION = {"nl": "Syndicaal afgevaardigde (BBTK)", "en": "Shop steward for Unite"}
HARD_FAMILY = {"nl": {True: "Papa van twee zonen en vlot in plannen.", False: "Mama van twee dochters en vlot in plannen."},
               "en": {True: "Dad of two sons and good at planning.", False: "Mum of two daughters and good at planning."}}
HARD_CRIME = {"nl": "In 2018 kreeg ik een werkstraf wegens diefstal.", "en": "In 2018 I received a community service order for theft."}
HARD_BORN = {"nl": "Geboren op {d} te {city}.", "en": "Born on {d} in {city}."}

# Valkuilen voor over-redactie: bevatten een trefwoord, maar zijn NIET gevoelig.
HARD_TRAPS = {"nl": ["Administratieve ondersteuning bij Stichting tegen Kanker.",
                     "Gaf een training over burn-out preventie aan teams.",
                     "Analyse van het proces rond strafblad-aanvragen voor de gemeente."],
              "en": ["Administrative support at the Cancer Research Foundation.",
                     "Delivered a training on burn-out prevention to teams.",
                     "Analysed the process for criminal record requests for the council."]}


def hard_date(d, lang, style):
    if style == 0:
        return f"{d:%Y-%m-%d}"
    if style == 1:
        return f"{d.day:02d}/{d.month:02d}/{d:%y}"
    return f"{MONTHS['en'][d.month - 1]} {d.day}, {d.year}" if lang == "en" else f"{d.day:02d}-{d.month:02d}-{d:%y}"


def hard_phone(rng):
    n = "".join(str(rng.randint(0, 9)) for _ in range(6))
    k = rng.choice([0, 1, 2])
    if k == 0:
        return f"0470/{n[:2]}.{n[2:4]}.{n[4:]}"
    if k == 1:
        return f"0470.{n[:2]}.{n[2:4]}.{n[4:]}"
    return f"+32 (0)470 {n[:2]} {n[2:4]} {n[4:]}"   # controle: dit formaat vindt de regex wel


def hard_address(fake, rng, city):
    return f"{fake.postcode()} {city}, {fake.street_name()} {rng.randint(1, 180)}"   # postcode eerst