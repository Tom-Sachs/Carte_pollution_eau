import requests
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
import altair as alt
import vega 

# Extraction des données 

url = "https://hubeau.eaufrance.fr/api/v1/qualite_rivieres/analyse_pc?code_departement=77&code_parametre=1385,1340,1107&code_qualification=1&size=5000&pretty&fields=code_station,libelle_station,code_parametre,libelle_parametre,date_prelevement,resultat,symbole_unite,code_qualification"

response = requests.get(url, {'Page': 1})
content = json.loads(response.content)['data']
Data = pd.DataFrame(columns = content[0].keys()).append(content)

pages = [2, 3, 4]

for i in pages:
    response = requests.get(url, {'Page': i})
    content = json.loads(response.content)['data']
    Data = Data.append(content)

# Extraction de la liste des stations et de leurs coordonnées géographiques

response = requests.get("https://hubeau.eaufrance.fr/api/v1/qualite_rivieres/station_pc?code_departement=77&fields=code_station,longitude,latitude,libelle_departement")
content = json.loads(response.content)['data']
liste_stations = pd.DataFrame(columns = content[0].keys())
liste_stations = liste_stations.append(content)

# Fusion des deux database (On fusionne les deux base de données afin de faire correspondre chaque station avec sa latitude et sa longitude)

Data = Data.merge(liste_stations, on = 'code_station')

# Traitement des données

# On enlève les relevés non qualifiés de la database, qui fausseraient les résultats
# NB: Utilisation de la méthode .loc() afin d'éviter SettingWithCopyWarning
Data = Data.loc[Data.code_qualification=='1']
Data_F = Data.reset_index()

# On crée trois dataset pour chaque feature, afin de créer trois graphiques différents plus facilement

Data_nitrates = Data_F.loc[Data_F.libelle_parametre=="Nitrates"]
Data_atrazine = Data_F.loc[Data_F.libelle_parametre=="Atrazine"]
Data_selenium = Data_F.loc[Data_F.libelle_parametre=="Sélénium"]

# On enlève les outliers

qn = Data_nitrates['resultat'].quantile(0.99)
Data_nitrates = Data_nitrates.loc[Data_nitrates.resultat<qn]

qa = Data_atrazine['resultat'].quantile(0.99)
Data_atrazine = Data_atrazine.loc[Data_atrazine.resultat<qa]

qs = Data_selenium['resultat'].quantile(0.99)
Data_selenium = Data_selenium.loc[Data_selenium.resultat<qs]

# Mise à jour de la liste de stations
liste_stations = Data_F.code_station.unique().tolist()

# Création de la carte interactive 

# Global tooltip
tooltip = 'Click To See Data'

# Create map object
m = folium.Map(location = [48.841082,2.999366], zoom_start = 9.4)

# LOOP FOR: Create markers for each station 

for i in liste_stations: 
    
    # Etape 1: Localisation de la station sur la carte grâce à ses coordonnées

    Data_station = Data_F.loc[Data_F.code_station==i]
    location = tuple([Data_station.iloc[0].latitude,Data_station.iloc[0].longitude])
    nom_station = str(Data_station.libelle_station.unique())
    
    # Etape 2: Création de trois graphiques avec les données 
   
    nitrates = {}
    nitrates['data'] = Data_nitrates[Data_nitrates.code_station==i]
    nitrates['title'] = 'Pollution en nitrates'
    
    selenium = {}
    selenium['data'] = Data_selenium[Data_selenium.code_station==i]
    selenium['title'] = 'Pollution en sélénium'
    
    atrazine = {}
    atrazine['data'] = Data_atrazine[Data_atrazine.code_station==i]
    atrazine['title'] = 'Pollution en atrazine'
    
    polluants = [nitrates, selenium, atrazine]
    charts = []
    
    for j in range(len(polluants)):
        charts.append(alt.Chart(polluants[j]['data'])\
        .mark_line()\
        .encode(alt.X('date_prelevement:T', timeUnit = 'yearmonth', title = 'Date du prélèvement'), alt.Y('resultat:Q', title = 'Quantité en mg/L'), alt.Color('libelle_parametre')).properties(width=200,height=100,title=polluants[j]['title']))
        
    Chart = alt.vconcat(charts[0], charts[1], charts[2])
    vis1 = Chart.to_json()
    
    # Etape 3: Création d'un marqueur avec les données en popup
    folium.Marker(location=location,
                  popup=folium.Popup(max_width=750).add_child(folium.VegaLite(vis1, width=390, height=500)),
                  tooltip=tooltip,icon=folium.Icon(icon='tint', color='darkblue')).add_to(m)

# Generate Map
m.save('map_pollution_eau_77.html')