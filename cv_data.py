"""Vaste tabellen voor de cv-generator: labels, jobs, skills, talen en de gevoelige zinnen."""
from datetime import date

TODAY = date(2026, 11, 1)
LOCALES = {"nl": "nl_BE", "en": "en_GB"}
MONTHS = {
    "nl": "januari februari maart april mei juni juli augustus september oktober november december".split(),
    "en": "January February March April May June July August September October November December".split(),
}
L = {  # labels per taal
    "nl": dict(personal="Persoonlijke gegevens", birth="Geboortedatum", nat="Nationaliteit", marital="Burgerlijke staat", children="Kinderen", address="Adres", phone="Telefoon", email="E-mail", profile="Profiel", jobs="Werkervaring", edu="Opleiding", skills="Vaardigheden", langs="Talen", extra="Vrijwilligerswerk en interesses", present="heden"),
    "en": dict(personal="Personal details", birth="Date of birth", nat="Nationality", marital="Marital status", children="Children", address="Address", phone="Phone", email="Email", profile="Profile", jobs="Work experience", edu="Education", skills="Skills", langs="Languages", extra="Volunteering and interests", present="present"),
}
MARITAL = {"nl": ["Gehuwd", "Ongehuwd", "Samenwonend", "Gescheiden"], "en": ["Married", "Single", "Cohabiting", "Divorced"]}
NATIONALITY = {"nl": ["Belgisch", "Nederlands", "Pools", "Marokkaans", "Turks"], "en": ["Belgian", "Dutch", "Polish", "Moroccan", "Turkish"]}
CHILDREN = {"nl": lambda n: f"{n} kinderen" if n > 1 else "1 kind", "en": lambda n: f"{n} children" if n > 1 else "1 child"}
JOBS = {  # (functietitel, passende taken)
    "nl": [("Administratief medewerker", ["Dagelijkse administratie en archivering", "Opmaak van facturen en rapporten", "Opvolging van e-mails en telefoons"]), ("Technicus onderhoud", ["Onderhoud van machines volgens checklist", "Opsporen en herstellen van storingen", "Naleven van veiligheidsvoorschriften"]), ("Klantendienstmedewerker", ["Opvolging van klantvragen", "Afhandelen van klachten", "Registratie van gesprekken in het CRM"]), ("Magazijnier", ["Voorraadbeheer en orderpicking", "Ontvangst en controle van goederen", "Besturen van de heftruck"]), ("Boekhoudkundig assistent", ["Opmaak van facturen en rapporten", "Boeken van leveranciersfacturen", "Opvolging van betalingen"]), ("HR-assistent", ["Ondersteuning bij werving en selectie", "Personeelsadministratie bijhouden", "Plannen van gesprekken met kandidaten"])],
    "en": [("Administrative assistant", ["Daily administration and filing", "Preparing invoices and reports", "Handling emails and phone calls"]), ("Maintenance technician", ["Machine maintenance following checklists", "Diagnosing and repairing faults", "Complying with safety procedures"]), ("Customer service agent", ["Handling customer requests", "Resolving complaints", "Logging conversations in the CRM"]), ("Warehouse operator", ["Stock management and order picking", "Receiving and checking goods", "Operating the forklift"]), ("Accounting assistant", ["Preparing invoices and reports", "Booking supplier invoices", "Following up on payments"]), ("HR assistant", ["Supporting recruitment and selection", "Maintaining personnel records", "Scheduling candidate interviews"])],
}
SKILLS = {"nl": ["Excel", "Word", "SAP", "Outlook", "Teamwerk", "Klantgericht werken", "Python", "SQL", "Heftruckcertificaat", "Veiligheidsvoorschriften", "Power BI", "Planning"],
          "en": ["Excel", "Word", "SAP", "Outlook", "Teamwork", "Customer focus", "Python", "SQL", "Forklift licence", "Safety procedures", "Power BI", "Planning"]}
EDU = {"nl": ["Bachelor Toegepaste Informatica", "Secundair onderwijs Handel", "Bachelor Office Management", "Technisch secundair Elektromechanica"],
       "en": ["Bachelor in Applied Computer Science", "Secondary education Business", "Bachelor in Office Management", "Technical secondary Electromechanics"]}
LANGS = {"nl": ["Nederlands", "Frans", "Engels", "Duits"], "en": ["Dutch", "French", "English", "German"]}
LEVELS = {"nl": ["basis", "gevorderd", "moedertaal"], "en": ["basic", "intermediate", "native"]}

# Gevoelige "lekken" in vrije tekst (de volledige zin is de waarde in de ground truth)
HEALTH = {"nl": ["Door mijn {c} werk ik het best in een rustige omgeving.", "Na mijn {c} in 2022 ben ik opnieuw volledig inzetbaar."],
          "en": ["Because of my {c} I work best in a calm environment.", "After my {c} in 2022 I am fully available again."]}
CONDITIONS = {"nl": ["dyslexie", "diabetes type 1", "burn-out", "rugklachten"], "en": ["dyslexia", "type 1 diabetes", "burn-out", "back problems"]}
RELIGION = {"nl": ["Vrijwilliger bij de parochie van {city}", "Lid van de Islamitische Gemeenschap {city}"],
            "en": ["Volunteer at {city} Parish", "Member of the {city} Islamic Community"]}
UNION = {"nl": "Actief lid van de vakbond ACV", "en": "Active member of a trade union"}
FAMILY = {"nl": "Als {w} van {n} kinderen ben ik flexibel georganiseerd.", "en": "As a {w} of {n} children I am flexibly organised."}
FAMILY_W = {"nl": {True: "vader", False: "moeder"}, "en": {True: "father", False: "mother"}}
CRIME = {"nl": "Veroordeeld voor een verkeersovertreding in 2019.", "en": "Convicted of a traffic offence in 2019."}
