"""Researched food & drink neighbourhoods per city (web search, 2026-11-24).

Each entry:
  name       display name
  lat, lng   approximate centre of the strip/neighbourhood (hand-placed)
  known_for  one line from the research
  weight     0-1, how strong a food/drink hotspot it is (drives the heat layer)
  candidate  True = used as a candidate meeting spot in the PoC;
             False = heat layer only (popular but usually not "in the middle")

This is static research. Phase 2 can replace or refresh it from live data
(e.g. counting highly rated places from the Places API) without changing
the shape.

Sources:
  London: lonelyplanet.com/articles/best-neighborhoods-in-london,
    guide.michelin.com (inspectors' favourite areas, Jan 2026),
    londonwebcam.co.uk/blog/best-areas-to-stay-in-london-for-nightlife,
    frommers.com London neighborhoods in brief
  San Francisco: sftravel.com/article/san-francisco-nightlife-neighborhood,
    lonelyplanet.com/articles/best-neighborhoods-in-san-francisco,
    matadornetwork.com (6 coolest neighborhoods to eat, drink, party)
  Munich: munich.travel (Glockenbachviertel & Gärtnerplatz; Where the night begins;
    Westend tips), lonelyplanet.com/articles/best-neighborhoods-in-munich,
    merian.de (angesagte Szeneviertel)
  Cape Town: capetown.travel/8-best-streets-for-a-cape-town-night-out,
    theculturetrip.com (Cape Town's trendiest neighbourhoods),
    timeout.com/cape-town
"""

HOT_NEIGHBOURHOODS: dict[str, list[dict]] = {
    "london": [
        {"name": "Soho", "lat": 51.5136, "lng": -0.1340, "weight": 1.0, "candidate": True,
         "known_for": "Heart of central nightlife: bars, pubs, live music, theatres"},
        {"name": "Covent Garden", "lat": 51.5117, "lng": -0.1240, "weight": 0.9, "candidate": True,
         "known_for": "West End restaurants and theatre-district bars"},
        {"name": "Fitzrovia", "lat": 51.5200, "lng": -0.1380, "weight": 0.7, "candidate": True,
         "known_for": "Sophisticated bars, quieter nightlife"},
        {"name": "King's Cross", "lat": 51.5357, "lng": -0.1253, "weight": 0.8, "candidate": True,
         "known_for": "Modern hub: Granary Square and Coal Drops Yard restaurants and bars"},
        {"name": "Shoreditch", "lat": 51.5246, "lng": -0.0786, "weight": 1.0, "candidate": True,
         "known_for": "Cocktail bars, pubs, clubs and live music"},
        {"name": "Southbank / Waterloo", "lat": 51.5050, "lng": -0.1140, "weight": 0.7, "candidate": True,
         "known_for": "Riverside bars and restaurants by the arts centres"},
        {"name": "Borough / Bermondsey", "lat": 51.5055, "lng": -0.0910, "weight": 0.9, "candidate": True,
         "known_for": "Borough Market food and restaurants south of the river"},
        {"name": "Islington (Upper Street)", "lat": 51.5390, "lng": -0.1030, "weight": 0.7, "candidate": True,
         "known_for": "Neighbourhood cafés and restaurants"},
        {"name": "Brixton", "lat": 51.4626, "lng": -0.1145, "weight": 0.8, "candidate": True,
         "known_for": "High-energy nights: O2 Academy, clubs, Brixton Village food"},
        {"name": "Dalston", "lat": 51.5465, "lng": -0.0753, "weight": 0.7, "candidate": True,
         "known_for": "East London bars, DJs and music venues"},
        {"name": "Hackney (Broadway Market)", "lat": 51.5361, "lng": -0.0617, "weight": 0.8, "candidate": True,
         "known_for": "Independent restaurants, foodie destination"},
        {"name": "Notting Hill", "lat": 51.5110, "lng": -0.2050, "weight": 0.8, "candidate": False,
         "known_for": "Michelin inspectors' favourite: multicultural food scene"},
    ],
    "sf": [
        {"name": "Mission / Valencia St", "lat": 37.7620, "lng": -122.4215, "weight": 1.0, "candidate": True,
         "known_for": "Top nightlife pick: DJ bars, Latin dance, restaurants"},
        {"name": "Hayes Valley", "lat": 37.7765, "lng": -122.4240, "weight": 0.8, "candidate": True,
         "known_for": "Cozy bars and restaurants along the main street"},
        {"name": "Lower Polk", "lat": 37.7880, "lng": -122.4200, "weight": 0.8, "candidate": True,
         "known_for": "Locals' favourite bars and sunny restaurants"},
        {"name": "SoMa / Yerba Buena", "lat": 37.7840, "lng": -122.4030, "weight": 0.7, "candidate": True,
         "known_for": "Bars and clubs"},
        {"name": "North Beach", "lat": 37.8003, "lng": -122.4100, "weight": 0.9, "candidate": True,
         "known_for": "Classic longtime bars, restaurants and cafés"},
        {"name": "Castro", "lat": 37.7609, "lng": -122.4350, "weight": 0.8, "candidate": True,
         "known_for": "Historic core of SF queer nightlife"},
        {"name": "Union Square", "lat": 37.7880, "lng": -122.4075, "weight": 0.6, "candidate": True,
         "known_for": "Cocktails and rooftop hotel bars"},
        {"name": "Financial District", "lat": 37.7946, "lng": -122.3999, "weight": 0.5, "candidate": True,
         "known_for": "After-work bars"},
        {"name": "Haight", "lat": 37.7692, "lng": -122.4481, "weight": 0.5, "candidate": True,
         "known_for": "Dive bars with character"},
        {"name": "Inner Richmond (Clement St)", "lat": 37.7830, "lng": -122.4650, "weight": 0.6, "candidate": True,
         "known_for": "Craft beer and Asian restaurants"},
        {"name": "Marina (Chestnut St)", "lat": 37.8003, "lng": -122.4370, "weight": 0.7, "candidate": False,
         "known_for": "Busy bar and brunch strip"},
    ],
    "munich": [
        {"name": "Glockenbachviertel", "lat": 48.1290, "lng": 11.5700, "weight": 1.0, "candidate": True,
         "known_for": "Best overall for restaurants, cocktail bars and nightlife; LGBTQ+ scene"},
        {"name": "Gärtnerplatz", "lat": 48.1316, "lng": 11.5765, "weight": 1.0, "candidate": True,
         "known_for": "Cocktail bars, craft-beer pubs, wine bars, late terraces"},
        {"name": "Sendlinger Tor", "lat": 48.1340, "lng": 11.5670, "weight": 0.7, "candidate": True,
         "known_for": "Central hub next to the Glockenbach scene"},
        {"name": "Maxvorstadt (Uni)", "lat": 48.1500, "lng": 11.5800, "weight": 0.8, "candidate": True,
         "known_for": "University district: cafés, restaurants, beer gardens, bars"},
        {"name": "Schwabing (Leopoldstraße)", "lat": 48.1580, "lng": 11.5850, "weight": 0.8, "candidate": True,
         "known_for": "Classic nightlife strip near the Englischer Garten"},
        {"name": "Haidhausen", "lat": 48.1290, "lng": 11.5960, "weight": 0.7, "candidate": True,
         "known_for": "Excellent local restaurants and beer gardens, fewer tourists"},
        {"name": "Bahnhofsviertel", "lat": 48.1395, "lng": 11.5600, "weight": 0.6, "candidate": True,
         "known_for": "Edgier, multicultural restaurants"},
        {"name": "Altstadt", "lat": 48.1374, "lng": 11.5755, "weight": 0.6, "candidate": True,
         "known_for": "Traditional beer halls"},
        {"name": "Westend", "lat": 48.1370, "lng": 11.5390, "weight": 0.5, "candidate": True,
         "known_for": "Local bars and restaurants"},
        {"name": "Schlachthofviertel", "lat": 48.1240, "lng": 11.5560, "weight": 0.6, "candidate": True,
         "known_for": "Bars and clubs around the old slaughterhouse"},
    ],
    "capetown": [
        {"name": "Bree Street", "lat": -33.9200, "lng": 18.4170, "weight": 1.0, "candidate": True,
         "known_for": "Buzziest street: stylish restaurants and cocktail bars"},
        {"name": "Gardens / Kloof Street", "lat": -33.9330, "lng": 18.4120, "weight": 0.9, "candidate": True,
         "known_for": "Bars, lounges and nightlife venues"},
        {"name": "De Waterkant", "lat": -33.9150, "lng": 18.4190, "weight": 0.8, "candidate": True,
         "known_for": "Bars and restaurants around the Cape Quarter"},
        {"name": "Green Point", "lat": -33.9080, "lng": 18.4070, "weight": 0.7, "candidate": True,
         "known_for": "Liberal, gay-friendly nightlife"},
        {"name": "Woodstock / Albert Road", "lat": -33.9270, "lng": 18.4470, "weight": 0.8, "candidate": True,
         "known_for": "Creative hub: restaurants, breweries, quirky bars"},
        {"name": "Observatory (Lower Main Rd)", "lat": -33.9375, "lng": 18.4710, "weight": 0.7, "candidate": True,
         "known_for": "Eclectic, alternative nightlife"},
        {"name": "Sea Point (Beach Road)", "lat": -33.9130, "lng": 18.3880, "weight": 0.7, "candidate": True,
         "known_for": "Restaurants and beach-side bars that turn into clubs"},
        {"name": "Claremont", "lat": -33.9820, "lng": 18.4650, "weight": 0.6, "candidate": True,
         "known_for": "Youthful, sociable nightlife"},
        {"name": "Camps Bay", "lat": -33.9510, "lng": 18.3780, "weight": 0.8, "candidate": False,
         "known_for": "Trendy oceanfront restaurants and bars"},
        {"name": "V&A Waterfront", "lat": -33.9050, "lng": 18.4200, "weight": 0.8, "candidate": False,
         "known_for": "Harbour restaurants and bars"},
    ],
}
