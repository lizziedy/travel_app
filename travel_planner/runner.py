from travel_app import controller, requester, models


if  __name__ =='__main__':
    """
    businesses = requester.get_yelp_request(term="restaurants", location="paris, france")
    business = models.YelpActivity.create(businesses[0])
    """
    controller.TravelAppCmdLine().cmdloop()
