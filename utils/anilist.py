import requests
import json
def search_results(name):
    query = '''
    query ($search: String) {
    Page(page: 1, perPage: 10) {
      pageInfo {
        total
        perPage
      }
      media(search: $search, type: ANIME, sort: FAVOURITES_DESC) {
        id
        title {
          english
        }
        seasonYear
        format
        episodes
      }
    }
  }
    '''
    variables = {
        'search': name
    }
    url = 'https://graphql.anilist.co'

    response = requests.post(url, json={'query': query, 'variables': variables})
    responsejson = json.loads(response.text.encode('utf8'))
    show_list = [{k:(0 if v is None else v) for k,v in {"id":x["id"],"title":x["title"]["english"],"year":x["seasonYear"],"format":x["format"],"episodes":x["episodes"]}.items()} for x in responsejson["data"]["Page"]["media"]]
    return show_list
