import requests
from selenium import webdriver
import time
import json
import backoff
import os
from datetime import datetime

#get data of airing shows from anilist
def pull_airing_data():
    SHOW_FORMATS = [
        "TV",
        "TV_SHORT",
        "MOVIE",
        "SPECIAL",
        "OVA",
        "ONA",
        "MUSIC",
    ]
    #headless browser driver installation path
    DRIVER_PATH = os.getenv('DRIVER_PATH')
    driver = webdriver.Firefox(executable_path=DRIVER_PATH)
    url ='https://anilist.co/search/anime?season='
    #calculate which anime season we're currently in
    doy = datetime.today().timetuple().tm_yday
    year = datetime.now().year
    if (year%4 == 0) and not (year%100 == 0):
        leapyear = 1
    else:
        leapyear = 0
    winter = range(0,90+leapyear)
    spring = range(90+leapyear,181+leapyear)
    summer = range(181+leapyear,273+leapyear)
    if doy in winter:
        url += "WINTER"
    elif doy in spring:
        url += "SPRING"
    elif doy in summer:
        url += "SUMMER"
    else:
        url += "FALL"
    #open webpage with driver
    driver.get(url)
    html = driver.page_source
    #scroll page to load all shows into view
    SCROLL_PAUSE_TIME = 2
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    #collect all anime from the loaded page
    anime_titles = driver.find_elements_by_class_name('title')
    anime_IDs = []
    for anime in anime_titles:
        #get the anilist IDs for all collected anime
        ID = anime.get_attribute('href').split("/")[4]
        anime_IDs.append(ID)
    #close the browser
    driver.quit()
    #populate JSON of anime data using IDs and anilist API queries
    anime_data = {}
    for format in SHOW_FORMATS:
        anime_data[format] = []
    for ID in anime_IDs:
        #pull metadata for a show to deduce format
        response = get_metadata(ID)
        format = response["data"]["Media"]["format"]
        try:
            anime_data[format].append(response)
        except KeyError:
            continue
    return anime_data

@backoff.on_exception(backoff.expo,json.decoder.JSONDecodeError,max_tries=3)
def get_metadata(ID):
    query = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
          title{
            romaji
          }
            format
        isAdult
        }
    }
    '''
    variables = {
        'id': ID,
    }
    url = 'https://graphql.anilist.co'
    response = requests.post(url, json={'query': query, 'variables': variables})
    response = json.loads(response.text.encode('utf8'))
    return response
