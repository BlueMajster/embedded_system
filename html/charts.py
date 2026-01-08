import streamlit as st
import streamlit_authenticator as stauth
import streamlit.components.v1 as components
import yaml
from yaml.loader import SafeLoader
import pandas as pd
import numpy as np
import time
import socket


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
    
# -------------------------------------------------------- KOD WOJTKA ------------
data = pd.DataFrame({
    'time': [1,2,3,4],
    'action': [0,0,1,1],
    'person': ['K','W','W','K'],
    'image': [0,0,0,0]})

def get_person_data(data:pd.DataFrame):
    people = np.unique(data['person'])
    people_action = []
    for i in range(len(people)):
        people_action.append([1])
    for i in range(len(data['time'])):
        for j in range(len(people)):
            if(data['person'][i] == people[j]):
                people_action[j].append(data['action'][i])
            else:
                people_action[j].append(people_action[j][-1])
    return pd.DataFrame({
        'person':people,
        'action':people_action
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
    person_data = get_person_data(data)
    st.dataframe(person_data,
                column_config={
                    'person': 'Person',
                    'action': st.column_config.BarChartColumn("Presence past X days",y_min=0,y_max=1)
                },
                hide_index=True)

    """Lokalizacja"""
    map_data = pd.DataFrame(
        [[52.5292182,17.5627153],[52.4011026,16.9514429]],
        columns=['lat', 'lon'])

    st.map(map_data,size=500)

    if st.checkbox("Pokaz czyste dane"):
        """
        Pełne dane:
        """
        data

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

# streamlit run ./charts.py --server.port 5000 --server.baseUrlPath=/wykresy