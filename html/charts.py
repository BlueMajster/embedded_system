import streamlit as st
import streamlit_authenticator as stauth
import streamlit.components.v1 as components
import yaml
from yaml.loader import SafeLoader
import pandas as pd
import numpy as np
import time
import socket
from pymongo import MongoClient
import datetime

# ------------ POŁĄCZENIE Z BAZĄ DANYCH ----------------------------
password = "f7r82rfa8eCvXpqT"
uri = f"mongodb+srv://BlueSky:{password}@mongolek.vmicgbi.mongodb.net/?appName=Mongolek"

try:
    client = MongoClient(uri)
    db = client["raspberry"]
    mongo_data = db["security"]
    print("Successfully connected to mongo db")
except Exception as e:
    print("Could not connect to db")
    client = None
    exit()

loaded_data = []
with mongo_data.find() as cursor:
    for i in cursor:
        loaded_data.append(i)

# --------- AUTORYZACJA Z CIASTECZKAMI NGINX --------------
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # imagine connecting to external server to see lan_ip
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

current_ip = get_lan_ip()
NGINX_ADDRESS = f"http://{current_ip}/"
COOKIE_NAME = "main_session"

# --- SPRAWDZANIE UPRAWNIEŃ ---
try:
    cookies = st.context.cookies
    if COOKIE_NAME in cookies:
        is_authorized = True
    else:
        is_authorized = None
except AttributeError:
    is_authorized = None

# Sprawdzenie flagi (dla pętli zwrotnej z Nginx)
if is_authorized is None:
    if st.query_params.get("verified") == "true":
        is_authorized = True

if is_authorized is True:
    pass
    
else:
    st.error("Authorization required. Redirecting...")

    time.sleep(1)
    meta_refresh = f'<meta http-equiv="refresh" content="0;url={NGINX_ADDRESS}">'
    st.markdown(meta_refresh, unsafe_allow_html=True)
    st.stop()
    
# ------ TABELA Z WYKRYTYMI OSOBAMI ----------------
def select_person_data(records: list[dict]) -> dict:
    if len(records) == 0: return None
    return_information = {"names":[],"entries":[],"leaves":[],"photos":[]}
    for i in records:
        if i["name"] not in return_information["names"]:
            return_information["names"].append(i['name'])
            return_information["entries"].append([])
            return_information["leaves"].append([])
            return_information["photos"].append([])
        curr_index = return_information["names"].index(i["name"])
        return_information["entries"][curr_index].append(i["entry_time"])
        return_information["leaves"][curr_index].append(i["exit_time"])
        return_information["photos"][curr_index].append(i["photo"])
    return return_information

def change_date_to_str(person_data):
    for i in range(len(person_data["names"])):
        for j in range(len(person_data["entries"][i])):
            person_data["entries"][i][j] = person_data["entries"][i][j].strftime("%d/%m/%Y  %H:%M:%S")
        for j in range(len(person_data["leaves"][i])):
            if person_data["leaves"][i][j] != None:
                person_data["leaves"][i][j] = person_data["leaves"][i][j].strftime("%d/%m/%Y  %H:%M:%S")
    return person_data

def get_30_last_days_dataframe(person_data):
    current_time = datetime.datetime.now()
    persons = person_data["names"]
    presence_last_days = []
    for i in range(len(persons)):
        presence_last_days.append([])
    found = False
    for k in range(30):
        checking_time = current_time + datetime.timedelta(days=k * -1)
        for i in range(len(persons)):
            for j in person_data["entries"][i]:
                if j.strftime("%d%m%Y") == checking_time.strftime("%d%m%Y"):
                    found = True
                    break
            if found == True:
                presence_last_days[i].append(1)
                found = False
            else:
                presence_last_days[i].append(0)
    return pd.DataFrame({
        'person':persons,
        'action':presence_last_days
    })

def get_curr_presence_dataframe(person_data):
    persons = person_data["names"]
    presence = []
    for i in range(len(persons)):
        found = False
        for j in person_data["leaves"][i]:
            if j == None:
                found = True
                break
        if found:
            presence.append("Present")
        else:
            presence.append("Absent")
    return pd.DataFrame({
        'person':persons,
        'presence':presence
    })


with open('credentials.yaml') as file:
    config = yaml.load(file,Loader=SafeLoader)
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['key'],
    config['cookie']['name'],
    config['cookie']['expiry_days']
)
authenticator.login(location='main')


if st.session_state["authentication_status"]:
    authenticator.logout()
    """Osoby monitorowane"""
    person_data = select_person_data(loaded_data)
    presence_data = get_30_last_days_dataframe(person_data)
    curr_presence_data = get_curr_presence_dataframe(person_data)

    st.dataframe(curr_presence_data,column_config={
        'person': 'Person',
        'presence': 'Presence'
    },hide_index=True)

    st.dataframe(presence_data,
                column_config={
                    'person': 'Person',
                    'action': st.column_config.BarChartColumn("Presence past X days",y_min=0,y_max=1,
                                                              help="The presence(entering the room) of person in the past 30 days")
                },
                hide_index=True)


    """Lokalizacja"""
    map_data = pd.DataFrame(
        [[52.5292182,17.5627153],[52.4011026,16.9514429],[52.2318412,21.0011241]],
        columns=['lat', 'lon'])
    st.map(map_data,size=500)

    if st.checkbox("Pokaz czyste dane"):
        """
        Pełne dane:
        """
        st.dataframe(change_date_to_str(person_data))
        loaded_data

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

# streamlit run ./charts.py --server.port 5000 --server.baseUrlPath=/wykresy
