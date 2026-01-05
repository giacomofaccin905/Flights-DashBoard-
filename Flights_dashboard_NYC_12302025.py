import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import folium
from streamlit_folium import st_folium
import pyreadr

TITLE_RED = "#8B0000"   # rosso scuro elegante
RED = "#ff4c4c"
DARK_BG = "#111111"



DARK_RED_THEME = dict(
    plot_bgcolor="#0B1C2D",
    paper_bgcolor="#0B1C2D",
    font=dict(color="white"),
    xaxis=dict(gridcolor="#2C3E50"),
    yaxis=dict(gridcolor="#2C3E50")
)


st.set_page_config(layout="wide")
st.title("NYC Flight Dashboard- Tracking & Delay")

@st.cache_data

def load_flight():
    result=pyreadr.read_r("nycflights.RData")
    df = result['nycflights']
    df=df.dropna(subset=["arr_delay"])
    return df

df = load_flight()


#####################################################################################################

@st.cache_data(ttl=60, show_spinner=False)

def get_live_flight():
    url= "https://opensky-network.org/api/states/all"    
    try:
        response = requests.get(
            url,
            auth=(st.secrets["OPENSKY_USER"], st.secrets["OPENSKY_PASS"]),
            timeout=10
        ) 
        response.raise_for_status()
        data= response.json()

        if "states" not in data or data["states"] is None:
            return pd.DataFrame()
        
    except requests.exceptions.RequestException as e:
        st.warning("Live flight data not available")
        return pd.DataFrame()    
    
    columns = ["icao24", "callsign", "origin_country", "time_position",
        "last_contact", "longitude", "latitude", "baro_altitude",
        "on_ground", "velocity", "heading", "vertical_rate",
        "sensors", "geo_altitude", "squawk", "spi", "position_source"
    ]
    df_live = pd.DataFrame(data["states"],columns=columns)
    df_live= df_live.dropna(subset=["latitude", "longitude"])
    return df_live

live_flights = get_live_flight()

REQUIRED_COLS = {"latitude", "longitude"}

if live_flights.empty or not REQUIRED_COLS.issubset(live_flights.columns):
    st.info("✈️ Live flight data temporarily unavailable")
    live_flights = pd.DataFrame(columns=["latitude", "longitude"])

#############################################################################################################

col1,col2,col3=st.columns(3)
col1.metric("Ongoing flighs",len(live_flights))
col2.metric("Average delay", round(df["arr_delay"].mean(), 2))
col3.metric(" Persentage Flights delay ", f"{round((df['arr_delay'] > 15).mean()*100, 1)} %")

## MAPPA INTERATTIVA

live_flights = live_flights.copy()
live_flights["latitude"] = pd.to_numeric(live_flights["latitude"], errors="coerce")
live_flights["longitude"] = pd.to_numeric(live_flights["longitude"], errors="coerce")
live_flights = live_flights.dropna(subset=["latitude", "longitude"])





st.markdown(
    f"<h3 style='color:{TITLE_RED}; margin-top:20px;'>  Real-time flight tracking </h3>",
    unsafe_allow_html=True
)

m = folium.Map(location=[40.7, -74], zoom_start=4)

for _, row in live_flights.head(300).iterrows():
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        popup_text= f""" <b>Flight:</b> {row['callsign']}<br>
        <b>Country:</b> {row['origin_country']}<br>
        <b>Velocity:</b>{round(row['velocity'],1)if pd.notna(row['velocity'])else 'N/A'}m/s <br>
        <b>Altitude:</b>{round(row['geo_altitude'],1)if pd.notna(row['geo_altitude'])else 'N/A'}m
        """
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            popup=popup_text,
            color="#ff4c4c",
            fill=True ,
            fill_color="#ff4c4c"
        ).add_to(m)
    except (ValueError, TypeError):
        continue

st_folium(m, width=1100, height=500)


##############################################################################################################


# Filter
st.markdown(
    f"<h3 style='color:{TITLE_RED}; margin-top:20px;'> Delay Analysis  </h3>",
    unsafe_allow_html=True
)

carrier= st.selectbox(
    "Select a company",options=sorted(df["carrier"].unique())
)

filtered = df[df["carrier"] == carrier]

## Boxplot

#st.subheader(' Arrival Delay Distribution ')

st.markdown(
    f"<h3 style='color:{TITLE_RED}; margin-top:20px;'>  Arrival Delay Distribution </h3>",
    unsafe_allow_html=True
)

fig_box= px.box(
    filtered,
    x = 'dest',
    y = 'arr_delay',
    color_discrete_sequence=['#ff4c4c'],
    points='outliers',
    labels={
        "dest": "Destination Airport",
        "arr_delay": "Arrival Delay (min)"
    },
    title= f" Delay Distribution by destination { carrier}"
)

fig_box.update_layout(**DARK_RED_THEME
)

fig_box.update_layout(
    title=dict(
        text=f"Delay Distribution by Destination – {carrier}",
        font=dict(color=TITLE_RED, size=20),
        x=0.5
    ),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)"
)



# Flights_dashboard_NYC_12302025.py

###############################################################################################################
delay_by_dest = (
    filtered.groupby("dest")["arr_delay"]
    .agg(mean_delay="mean", var_delay="var")
    .sort_values(by="mean_delay", ascending=False)
    .head(10)
    .reset_index()
)

fig = px.bar(
    delay_by_dest,
    x="dest",
    y=["mean_delay", "var_delay"],
    barmode="group",
    color_discrete_sequence=["#ff4c4c", "#ff9999"],
    title=f"Mean & Variance of delay – {carrier}",
    labels={"value": "Minutes", "dest": "Airport"}
)
fig.update_layout(**DARK_RED_THEME)

fig.update_layout(
    title=dict(
        text=f"Mean & Variance of delay – {carrier}",
        font=dict(color=TITLE_RED, size=20),
        x=0.5   # centra il titolo
    ),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)"
)


col_left,col_right=st.columns(2)

with col_left:
    st.plotly_chart(fig, width='content')

with col_right:
    st.plotly_chart(fig_box,width='content')



st.markdown(
    f"<h3 style='color:{TITLE_RED}; margin-top:20px;'>  Flight details</h3>",
    unsafe_allow_html=True
)

st.dataframe(
    filtered[["flight", "origin", "dest", "arr_delay"]].head(50)
)

