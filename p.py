import streamlit as st
import google.generativeai as genai
import os
import json
import streamlit.components.v1 as components
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import requests
from duckduckgo_search import DDGS
from datetime import datetime, timedelta


load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Google API key is missing! Please check your .env file.")
    st.stop()


genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-pro-exp-02-05")

geolocator = Nominatim(user_agent="ai_travel_planner", timeout=10)

currency_symbols = {
    "USD": "$", "EUR": "€", "INR": "₹", "GBP": "£", "JPY": "¥", "AUD": "A$", "CAD": "C$"
}


def get_coordinates(place):
    try:
        location = geolocator.geocode(place)
        if location:
            
            image_url = get_wikipedia_image(place)
            return {
                "name": place,
                "lon": location.longitude,
                "lat": location.latitude,
                "image_url": image_url
            }
    except GeocoderTimedOut:
        return get_coordinates(place)  
    return None  


def get_wikipedia_image(place):
    try:
        search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{place.replace(' ', '_')}"
        response = requests.get(search_url)
        if response.status_code == 200:
            data = response.json()
            if "thumbnail" in data:
                return data["thumbnail"]["source"]  
    except:
        return "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"  
    


def generate_itinerary(source, destination, duration, budget, currency, theme):
    prompt = f"""
    Plan a {duration}-day trip from {source} to {destination} within {budget} {currency}.
    The trip should be themed as **{theme}**. 

    Provide:
    - A detailed itinerary with day-wise places to visit.
    - A JSON list of place names (excluding source) that will be visited.
    Output format:
    
    [ "Place1", "Place2", "Place3", "Place4" ]
    """

    response = model.generate_content(prompt)

    if response and hasattr(response, 'text'):
        text_response = response.text

        
        try:
            json_start = text_response.find("[")
            json_end = text_response.rfind("]") + 1
            places_json_str = text_response[json_start:json_end]
            places_list = json.loads(places_json_str)
        except (json.JSONDecodeError, ValueError, IndexError):
            places_list = []

        itinerary_text = text_response[:json_start].strip()
    else:
        itinerary_text = "Failed to generate itinerary."
        places_list = []

    return itinerary_text, places_list


def get_hotel_image(hotel_name, destination):
    try:
        query = f"{hotel_name} {destination} hotel"
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
        if results:
            return results[0]["image"]
    except:
        pass
    return "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"  # Fallback Image



def get_budget_hotels(destination, budget, currency):
    prompt = f"""
    Suggest 5 budget-friendly hotels or Airbnbs near {destination} that fit within {budget} {currency} per night.
    Provide output in JSON format:
    
    [
        {{"name": "Hotel1", "price": 100, "location": "Area1"}},
        {{"name": "Hotel2", "price": 80, "location": "Area2"}},
        {{"name": "Hotel3", "price": 120, "location": "Area3"}},
        {{"name": "Hotel4", "price": 100, "location": "Area4"}},
        {{"name": "Hotel5", "price": 200, "location": "Area5"}}
    ]
    """

    response = model.generate_content(prompt)

    if response and hasattr(response, 'text'):
        try:
            json_start = response.text.find("[")
            json_end = response.text.rfind("]") + 1
            hotels_json_str = response.text[json_start:json_end]
            hotels_list = json.loads(hotels_json_str)
        except (json.JSONDecodeError, ValueError, IndexError):
            hotels_list = []
    else:
        hotels_list = []

    return hotels_list

# UI STYLES

st.set_page_config(layout="wide")
st.markdown("""
    <style>
        /* Background Styling */
        body {
            background-color: #f4f4f4;
        }

        /* Title Styling */
        .title {
            font-size: 40px;
            font-weight: bold;
            color: #ffffff;
            text-align: center;
            padding: 15px;
            background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
            border-radius: 10px;
            margin-bottom: 20px;
        }

        /* Container Styling */
        .stApp {
            background-image: url('https://source.unsplash.com/1600x900/?travel');
            background-size: cover;
            background-position: center;
            padding: 30px;
        }

        /* Input Styling */
        .stTextInput, .stNumberInput, .stSelectbox {
            border-radius: 8px;
            border: 2px solid #203a43;
            padding: 10px;
        }

        /* Button Styling */
        .stButton>button {
            background-color: #007BFF;
            color: white;
            font-size: 18px;
            padding: 10px 15px;
            border-radius: 10px;
            width: 100%;
        }

        .stButton>button:hover {
            background-color: #0056b3;
        }

        /* Card Styling */
        .card {
            background: linear-gradient(to right, #b3e5fc, #81d4fa, #4fc3f7);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            margin: 10px 0;
            color: black;
        }
    </style>
""", unsafe_allow_html=True)


# UI GENERATION

st.markdown("<div class='title'>🌍 AI Travel Planner 🚀</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3) 
col4, col5, col6 = st.columns(3)  

with col1:
    source = st.text_input("🏠 Source Location")

with col2:
    destination = st.text_input("📍 Destination Location")

with col3:
    duration = st.number_input("🗓 Duration of Trip (days)", min_value=1, max_value=30, value=3)

with col4:
    currency = st.selectbox("💲 Select Currency", list(currency_symbols.keys()))

with col5:
    budget = st.number_input(f"💰 Your Budget ({currency_symbols[currency]})", min_value=50, value=500)

with col6:
    theme = st.selectbox("🎭 Travel Theme", ["Adventure", "History", "Food", "Nature", "Romantic", "Luxury", "Backpacking"])

if st.button("🚀 Generate Trip Plan & Map", use_container_width=True):
    st.write(f"🌍 Planning a **{theme}** trip from **{source}** to **{destination}**...")

    
    itinerary, places_list = generate_itinerary(source, destination, duration, budget, currency, theme)

    st.markdown("### 📌 Trip Summary")
    st.write(f"<div class='card'>{itinerary[:200]}...</div>", unsafe_allow_html=True)

    with st.expander("📖 Full Itinerary"):
        st.markdown(f"<div class='card'>{itinerary}</div>", unsafe_allow_html=True)

    st.markdown("### 🏨 Budget-Friendly Hotels & Airbnbs")
    hotels = get_budget_hotels(destination, budget, currency)
    current_date = datetime.today().strftime("%Y-%m-%d")
    end_date = (datetime.today() + timedelta(days=duration)).strftime("%Y-%m-%d")

    if hotels:
        for hotel in hotels:
            hotel_name = hotel["name"]
            hotel_price = hotel["price"]
            hotel_location = hotel["location"]
            hotel_image = get_hotel_image(hotel_name, destination) 
            
            
            search_query = f"{hotel_name}"
            hotel_link = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            with st.container():
                st.markdown("<br>", unsafe_allow_html=True)
                col1, col2 = st.columns([7, 1])  

                with col1:  
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(to right, #b3e5fc, #81d4fa, #4fc3f7);
                                    padding: 15px; border-radius: 10px;
                                    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
                                    display: flex; align-items: center; height: 120px;">
                            <div style="flex: 1; text-align: left;">
                                <a href="{hotel_link}" target="_blank" 
                                style="font-size: 18px; font-weight: bold; color: #0056b3; text-decoration: none;">
                                    🏨 {hotel_name}
                                </a><br>
                                <span style="color: black;">💰 {currency_symbols[currency]}{hotel_price} per night</span><br>
                                <span style="color: black;">📍 {hotel_location}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col2: 
                    st.markdown(
                        f"""
                        <span style="height: 120px; width: 120px; display: flex; justify-content: center; align-items: center;">
                            <img src="{hotel_image}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">
                        </span>
                        """,
                        unsafe_allow_html=True,
                    )
    else:
        st.warning("No budget hotels found.")


    # MAP
    locations = []
    failed_places = []

    for place in places_list:
        coords = get_coordinates(place)
        if coords:
            locations.append(coords)
        else:
            failed_places.append(place)

    locations_json = json.dumps(locations)


    if locations:
        locations_json = json.dumps(locations)
        st.markdown("<br>", unsafe_allow_html=True)
        map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Route Map</title>
            <style>#map {{ width: 100%; height: 500px; }}</style>
            <script src="https://unpkg.com/ol@latest/dist/ol.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/ol@latest/dist/ol.css" />
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = new ol.Map({{
                    target: 'map',
                    layers: [
                        new ol.layer.Tile({{
                            source: new ol.source.OSM()
                        }})
                    ],
                    view: new ol.View({{
                        center: ol.proj.fromLonLat([{locations[0]['lon']}, {locations[0]['lat']}]),
                        zoom: 10
                    }})
                }});

                var places = {json.dumps(locations)};
                var markers = [];
                var overlayElement = document.createElement('div');
                overlayElement.style.background = "white";
                overlayElement.style.padding = "10px";
                overlayElement.style.borderRadius = "5px";
                overlayElement.style.boxShadow = "0px 0px 5px rgba(0, 0, 0, 0.5)";
                overlayElement.style.display = "none"; // Hide by default

                var overlay = new ol.Overlay({{
                    element: overlayElement,
                    positioning: 'bottom-center',
                    offset: [0, -10]
                }});
                map.addOverlay(overlay);

                places.forEach(place => {{
                    var marker = new ol.Feature({{
                        geometry: new ol.geom.Point(ol.proj.fromLonLat([place.lon, place.lat])),
                        name: place.name,
                        wikipedia_url: "https://en.wikipedia.org/wiki/" + encodeURIComponent(place.name.replace(/ /g, '_')),
                        image_url: place.image_url || 'https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg'
                    }});

                    var markerStyle = new ol.style.Style({{
                        image: new ol.style.Icon({{
                            src: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
                            scale: 1
                        }})
                    }});

                    marker.setStyle(markerStyle);
                    markers.push(marker);
                }});

                var vectorSource = new ol.source.Vector({{
                    features: markers
                }});

                var vectorLayer = new ol.layer.Vector({{
                    source: vectorSource
                }});

                map.addLayer(vectorLayer);

                map.on('pointermove', function(event) {{
                    var feature = map.forEachFeatureAtPixel(event.pixel, function(feature) {{
                        return feature;
                    }});

                    if (feature) {{
                        overlayElement.innerHTML = `<b>${{feature.get('name')}}</b><br>
                                                    <img src="${{feature.get('image_url')}}" width="150px" height="100px">`;
                        overlay.setPosition(event.coordinate);
                        overlayElement.style.display = "block";
                    }} else {{
                        overlay.setPosition(undefined);
                        overlayElement.style.display = "none";
                    }}
                }});

                map.on('contextmenu', function(event) {{
                    var feature = map.forEachFeatureAtPixel(event.pixel, function(feature) {{
                        return feature;
                    }});

                    if (feature) {{
                        window.open(feature.get('wikipedia_url'), '_blank');
                    }}
                }});
            </script>
        </body>
        </html>
        """

        
        components.html(map_html, height=550)
    else:
        st.error("Could not extract valid locations from the itinerary.")
