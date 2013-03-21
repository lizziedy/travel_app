import oauth2 as oauth
import json
import urllib

CONSUMER_KEY = "fnVPjkU_pufVuwXVX1QjwA"
CONSUMER_SECRET = "o7mLMG4WZsQT5xnwByyOwo6LVso"
TOKEN_KEY = "L0rJDIGgmDCgAP2EOWIVkZiSPcKSKKmD"
TOKEN_SECRET = "YtNYAQp3CQTD0akIY2y_XWkax1Q"

TOKEN = oauth.Token(key=TOKEN_KEY, secret=TOKEN_SECRET)
CONSUMER = oauth.Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET)


def list_items_pretty(businesses):
    i = 1
    for business in businesses:
        num_rating = business["rating"]
        rating = ""
        for _ in range(int(num_rating)):
            rating += "*"
        if int(num_rating) < num_rating:
            rating += "."
        
        print "[" + str(i) + "] " + business["name"] + " " + \
            rating + " (number of reviews: " + \
            str(business['review_count']) + ")"
        
        i += 1

def get_yelp_business_info(business_id, lang = None):
    params = {}
    if not lang:
        lang = "en"
    params["lang"] = lang
    params["lang_filter"] = True
    
    business_id = urllib.quote(business_id.encode("utf8"))#urllib.urlencode(business_id)
    r = oauth.Request(method="GET", 
                      url="http://api.yelp.com/v2/business/"+business_id,
                      parameters = params) 
    client = oauth.Client(CONSUMER, TOKEN)
        
    resp, content = client.request(r.to_url(), "GET")
    print resp["status"]
    if resp["status"] == "200":
        return json.loads(content)
    else:
        raise Exception(content)

def get_yelp_request(category_filter = None,
                     location = None,
                     term = None,
                     limit = None,
                     offset = None,
                     sort = None,
                     radius_filter = None,
                     deals_filter = None,
                     cc = None,
                     lang = None,
                     bounds = None,
                     ll = None,
                     cll = None):
    params = {}
    if category_filter:
        params["category_filter"] = category_filter
    if location:
        params["location"] = location
    if term:
        params["term"] = term
    if limit:
        params["limit"] = limit
    if sort:
        params["sort"] = sort
    if radius_filter:
        params["radius_filter"] = radius_filter
    if deals_filter:
        params["deals_filter"] = deals_filter
    if cc:
        params["cc"] = cc
    if not lang:
        lang = "en"
    params["lang"] = lang
    params["lang_filter"] = True
    if bounds:
        params["bounds"] = bounds
    if ll:
        params["ll"] = ll
    if cll:
        params["cll"] = cll

    if not offset:
        offset = 0


    businesses = []
    """
    done = False
    while not done:
        params["offset"] = offset
        r = oauth.Request(method="GET", 
                          url="http://api.yelp.com/v2/search", 
                          parameters = params)
        client = oauth.Client(CONSUMER, TOKEN)
        
        resp, content = client.request(r.to_url(), "GET")
    
        if resp["status"] == "200":
            response = json.loads(content)
            if len(response["businesses"]) == 0:
                done = True
            else:
                offset += len(response["businesses"])
                if offset >= 60:
                    done = True
            businesses = businesses + response["businesses"]
        else:
            raise Exception(content)
    """
    params["offset"] = offset
    r = oauth.Request(method="GET", 
                      url="http://api.yelp.com/v2/search", 
                      parameters = params)
    client = oauth.Client(CONSUMER, TOKEN)
        
    resp, content = client.request(r.to_url(), "GET")
    
    if resp["status"] == "200":
        response = json.loads(content)
        businesses = businesses + response["businesses"]
    else:
        raise Exception(content)
    return businesses
    
