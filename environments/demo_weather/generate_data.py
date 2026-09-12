"""Regenerate this environment's fake 'Nimbus Home Weather Co.' data/*.csv files, with the
same deliberately-implanted data-quality problems documented in README.md, from scratch.
Deterministic (fixed seed) -- re-running this reproduces byte-identical output.

    python generate_data.py
"""
import csv
import random
from pathlib import Path

random.seed(20260912)

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

FIRST_NAMES = ["Ava","Liam","Maya","Noah","Zoe","Ethan","Priya","Omar","Chloe","Diego",
               "Nina","Kai","Freya","Luca","Amara","Theo","Sana","Ravi","Elle","Jamal",
               "Ines","Milo","Yuki","Beth","Otis","Dara"]
LAST_NAMES = ["Nguyen","Patel","Garcia","Kim","Johnson","Rossi","Muller","Silva","Haddad",
              "Larsen","Okafor","Ivanov","Tanaka","Fischer","Costa","Novak","Diallo",
              "Sorensen","Byrne","Wallace","Petrov","Tremblay"]
VALID_STATES = ["CA","NY","TX","WA","CO","OR","AZ","IL","MA","NC","MN","GA","UT","VA","MI"]
CITIES = {"CA":"San Marcos","NY":"Rye","TX":"Round Rock","WA":"Bellingham","CO":"Golden",
          "OR":"Bend","AZ":"Tempe","IL":"Naperville","MA":"Salem","NC":"Cary",
          "MN":"Duluth","GA":"Marietta","UT":"Provo","VA":"Reston","MI":"Ann Arbor"}
ACCOUNT_STATUSES = ["ACTIVE","ACTIVE","ACTIVE","INACTIVE","SUSPENDED"]

N_CUSTOMERS = 26

customers = []
for i in range(1, N_CUSTOMERS + 1):
    cid = i
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    state = random.choice(VALID_STATES)
    signup = f"20{random.randint(21,26):02d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    status = random.choice(ACCOUNT_STATUSES)
    points = random.randint(0, 5000)
    customers.append({
        "CUSTOMER_ID": cid, "FIRST_NAME": fn, "LAST_NAME": ln, "SIGNUP_DATE": signup,
        "STATE_CD": state, "ACCOUNT_STATUS": status, "LOYALTY_POINTS": points,
    })

# --- implant problems into CUSTOMERS ---
customers[4]["LAST_NAME"] = ""                      # row idx4 (CUSTOMER_ID 5): null last name
customers[7]["STATE_CD"] = "ZZ"                      # CUSTOMER_ID 8: invalid state code
customers[10]["LOYALTY_POINTS"] = -150               # CUSTOMER_ID 11: negative points
customers[13]["SIGNUP_DATE"] = "sometime last spring"  # CUSTOMER_ID 14: unparseable date
# NOTE: NOT "N/A" -- pandas' default na_values list (see read_csv docs) treats "N/A",
# "NA", "NULL", "None", etc. as missing values, silently turning a malformed-string test
# into a null test before gx even sees the column. Use a garbled-but-not-NA-like string
# to actually exercise ExpectColumnValuesToBeDateutilParseable.
customers[16]["ACCOUNT_STATUS"] = "CANCELLED"        # CUSTOMER_ID 17: not in allowed set
customers[25]["CUSTOMER_ID"] = customers[9]["CUSTOMER_ID"]  # last row duplicates CUSTOMER_ID 10

with open(OUT / "CUSTOMERS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(customers[0].keys()))
    w.writeheader()
    w.writerows(customers)

# --- ADDRESSES: one per customer (except the duplicated-id row, which shares its customer) ---
addresses = []
aid = 1
for c in customers[:-1]:  # skip the duplicate-id row -- it "is" customer 10 for address purposes
    cid = c["CUSTOMER_ID"]
    state = c["STATE_CD"] if c["STATE_CD"] in CITIES else random.choice(VALID_STATES)
    city = CITIES[state]
    zip_code = f"{random.randint(10000,99999)}"
    addresses.append({
        "ADDRESS_ID": aid, "CUSTOMER_ID": cid,
        "STREET": f"{random.randint(100,9999)} {random.choice(['Maple','Birch','2nd','Sunset','River','Pine'])} {random.choice(['St','Ave','Ln','Dr'])}",
        "CITY": city, "STATE_CD": state, "BILLING_STATE_CD": state,
        "ZIP_CODE": zip_code, "COUNTRY_CD": "US",
    })
    aid += 1

addresses[2]["ZIP_CODE"] = "123"            # ADDRESS_ID 3: wrong length
addresses[6]["BILLING_STATE_CD"] = "TX" if addresses[6]["STATE_CD"] != "TX" else "NY"  # ADDRESS_ID 7: mismatch
addresses[9]["COUNTRY_CD"] = "USA"          # ADDRESS_ID 10: not "US"
addresses[12]["STREET"] = ""                # ADDRESS_ID 13: blank street

with open(OUT / "ADDRESSES.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(addresses[0].keys()))
    w.writeheader()
    w.writerows(addresses)

# --- PHONES: 1-2 per customer ---
phones = []
pid = 1
for c in customers[:-1]:
    cid = c["CUSTOMER_ID"]
    n_phones = random.choice([1, 1, 2])
    types_used = []
    for _ in range(n_phones):
        ptype = random.choice(["MOBILE","HOME","WORK"])
        while ptype in types_used:
            ptype = random.choice(["MOBILE","HOME","WORK"])
        types_used.append(ptype)
        number = f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
        phones.append({
            "PHONE_ID": pid, "CUSTOMER_ID": cid, "PHONE_TYPE": ptype,
            "PHONE_NUMBER": number, "IS_PRIMARY": 1 if _ == 0 else 0,
        })
        pid += 1

phones[4]["PHONE_NUMBER"] = "555.12.34"      # PHONE_ID 5: malformed
phones[9]["PHONE_TYPE"] = "FAX"              # PHONE_ID 10: not in allowed set
phones[-1]["PHONE_ID"] = phones[3]["PHONE_ID"]  # last row duplicates PHONE_ID 4

with open(OUT / "PHONES.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(phones[0].keys()))
    w.writeheader()
    w.writerows(phones)

# --- EMAILS: 1 per customer ---
emails = []
eid = 1
used_emails = set()
for c in customers[:-1]:
    cid = c["CUSTOMER_ID"]
    local = f"{c['FIRST_NAME'].lower()}.{c['LAST_NAME'].lower() or 'user'}{cid}"
    addr = f"{local}@example.com"
    emails.append({
        "EMAIL_ID": eid, "CUSTOMER_ID": cid, "EMAIL_ADDRESS": addr,
        "IS_VERIFIED": random.choice([1, 1, 1, 0]),
    })
    eid += 1

emails[5]["EMAIL_ADDRESS"] = "not-an-email"          # EMAIL_ID 6: malformed
emails[15]["EMAIL_ADDRESS"] = ""                      # EMAIL_ID 16: blank
emails[20]["EMAIL_ADDRESS"] = emails[2]["EMAIL_ADDRESS"]  # EMAIL_ID 21: duplicate of EMAIL_ID 3

with open(OUT / "EMAILS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(emails[0].keys()))
    w.writeheader()
    w.writerows(emails)

# --- STATIONS: ~15 customers own one ---
MODELS = ["WX100","WX200","WX300"]
station_owners = random.sample([c["CUSTOMER_ID"] for c in customers[:-1]], 15)
stations = []
sid = 1
for cid in station_owners:
    install = f"20{random.randint(23,26):02d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    wstart = install
    wend = f"20{int(install[2:4])+2:02d}{install[4:]}"
    stations.append({
        "STATION_ID": sid, "CUSTOMER_ID": cid, "MODEL_CD": random.choice(MODELS),
        "INSTALL_DATE": install, "WARRANTY_START_DATE": wstart, "WARRANTY_END_DATE": wend,
        "IS_ACTIVE": 1,
    })
    sid += 1

stations[3]["WARRANTY_END_DATE"] = stations[3]["WARRANTY_START_DATE"]  # STATION_ID 4: end == start (not >)
stations[7]["MODEL_CD"] = "WX50"                                       # STATION_ID 8: not in allowed set
stations.append(dict(stations[1]))                                    # duplicate STATION_ID (copy of station 2)
stations[-1]["STATION_ID"] = stations[1]["STATION_ID"]

with open(OUT / "STATIONS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(stations[0].keys()))
    w.writeheader()
    w.writerows(stations)

# --- READINGS: ~10 per real station (skip the appended duplicate-STATION_ID row) ---
real_stations = stations[:15]  # the 15 originally-generated stations; index 15 is the appended duplicate-STATION_ID row
readings = []
rid = 1
for st in real_stations:
    station_id = st["STATION_ID"]
    base_temp = random.uniform(45, 75)
    for day in range(1, 11):
        ts = f"2026-08-{day:02d}T{random.randint(6,20):02d}:00:00"
        temp = round(base_temp + random.uniform(-8, 8), 1)
        humidity = round(random.uniform(30, 85), 1)
        pressure = round(random.uniform(985, 1025), 1)
        wind = round(random.uniform(0, 22), 1)
        rain = round(random.choice([0, 0, 0, 0.02, 0.15, 0.4]), 2)
        battery = random.randint(55, 100)
        readings.append({
            "READING_ID": rid, "STATION_ID": station_id, "READING_TS": ts,
            "TEMPERATURE_F": temp, "HUMIDITY_PCT": humidity, "PRESSURE_HPA": pressure,
            "WIND_SPEED_MPH": wind, "RAINFALL_IN": rain, "BATTERY_PCT": battery,
        })
        rid += 1

# implant numeric problems at fixed, easy-to-find indices
readings[12]["HUMIDITY_PCT"] = 142.0          # READING_ID 13: >100
readings[27]["TEMPERATURE_F"] = -999.0        # READING_ID 28: sentinel/impossible outlier
readings[40]["PRESSURE_HPA"] = ""             # READING_ID 41: null
readings[55]["WIND_SPEED_MPH"] = -5.0         # READING_ID 56: negative
readings[70]["BATTERY_PCT"] = 137             # READING_ID 71: >100
readings[85]["RAINFALL_IN"] = -0.1            # READING_ID 86: negative
readings[100]["READING_TS"] = "not-a-timestamp"  # READING_ID 101: unparseable
# duplicate (STATION_ID, READING_TS) pair: copy row 5 (idx 5) onto row 6's identity but keep unique READING_ID
dup = dict(readings[5])
dup["READING_ID"] = rid
readings.append(dup)  # same STATION_ID + READING_TS as readings[5] -> compound-uniqueness violation
rid += 1

with open(OUT / "READINGS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(readings[0].keys()))
    w.writeheader()
    w.writerows(readings)

print("customers:", len(customers))
print("addresses:", len(addresses))
print("phones:", len(phones))
print("emails:", len(emails))
print("stations:", len(stations))
print("readings:", len(readings))
