from django.db import models

# Create your models here.

class DbObject(models.Model):
    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)

    class Meta:
        abstract = True

class Coordinate(models.Model):
    latitude = models.DecimalField(max_digits=48, decimal_places = 32)
    longitude = models.DecimalField(max_digits=48, decimal_places = 32)

    
    @staticmethod
    def create(yelp_coordinate):
        if Coordinate.exists(yelp_coordinate):
            raise Exception("This coordinate already exists in the database")

        o = Coordinate()
        o.latitude = yelp_coordinate["latitude"]
        o.longitude = yelp_coordinate["longitude"]
        o.save()
        return o

    @staticmethod
    def exists(yelp_coordinate):
        return Coordinate.get(yelp_coordinate) != None

    @staticmethod
    def get(yelp_coordinate):
        coordinates = Coordinate.objects.filter(latitude=yelp_coordinate["latitude"], 
                                               longitude=yelp_coordinate["longitude"])
        
        if len(coordinates) > 0:
            return coordinates[0]
        return None

    @staticmethod
    def get_or_create(yelp_coordinate):
        coordinate = Coordinate.get(yelp_coordinate)
        if not coordinate:
            coordinate = Coordinate.create(yelp_coordinate)
            
        return coordinate

class YelpCategory(models.Model):
    name = models.CharField(max_length=128)
    search_name = models.CharField(max_length=128)
    
    @staticmethod
    def create(yelp_category):
        if YelpCategory.exists(yelp_category):
            raise Exception("This category already exists in the database")

        o = YelpCategory()
        o.name = yelp_category[0]
        o.search_name = yelp_category[1]
        o.save()
        return o

    @staticmethod
    def exists(yelp_category):
        return YelpCategory.get(yelp_category) != None

    @staticmethod
    def get(yelp_category):
        categories = YelpCategory.objects.filter(name = yelp_category[0], search_name=yelp_category[1])
        
        if len(categories) > 0:
            return categories[0]
        return None

    @staticmethod
    def get_or_create(yelp_category):
        category = YelpCategory.get(yelp_category)
        if not category:
            category = YelpCategory.create(yelp_category)
            
        return category
    
    

class YelpNeighborhood(models.Model):
    name = models.CharField(max_length=128)

    @staticmethod
    def create(yelp_neighborhood):
        if YelpNeighborhood.exists(yelp_neighborhood):
            raise Exception("This neighborhood already exists in the database")
        
        o = YelpNeighborhood()
        o.name = yelp_neighborhood
        o.save()
        
    @staticmethod
    def exists(yelp_neighborhood):
        return YelpNeighborhood.get(yelp_neighborhood) != None
    
    @staticmethod
    def get(yelp_neighborhood):
        neighborhoods = YelpNeighborhood.objects.filter(name = yelp_neighborhood)
        if len(neighborhoods) > 0:
            return neighborhoods[0] 
        return None 

    @staticmethod
    def get_or_create(yelp_neighborhood):
        neighborhood = YelpNeighborhood.get(yelp_neighborhood)
        if not neighborhood:
            neighborhood = YelpNeighborhood.create(yelp_neighborhood)
            
        return neighborhood

class YelpLocation(models.Model):
    city = models.CharField(max_length=128)
    display_address = models.CharField(max_length=512)
    geo_accuracy = models.FloatField(default=9)
    neighborhoods = models.ManyToManyField(YelpNeighborhood, blank=True)
    postal_code = models.CharField(max_length=32)
    country_code = models.CharField(max_length=8)
    address = models.CharField(max_length=512)
    state_code = models.CharField(max_length=8, blank=True)
    coordinate = models.ForeignKey(Coordinate)

    @staticmethod
    def create(yelp_location):
        if YelpLocation.exists(yelp_location):
            raise Exception("This location already exists in the database")

        o = YelpLocation()        
        o.city = yelp_location["city"]
        o.display_address = yelp_location["display_address"]
        o.geo_accuracy = yelp_location["geo_accuracy"]
        o.postal_code = yelp_location["postal_code"]
        o.country_code = yelp_location["country_code"]
        o.address = yelp_location["address"]
        o.state_code = yelp_location["state_code"]

        db_coordinate = Coordinate.get(yelp_location["coordinate"])
        if not db_coordinate:
            db_coordinate = Coordinate.create(yelp_location["coordinate"])
        if db_coordinate: 
            o.coordinate = db_coordinate
        
        o.save()

        # adds categories to database
        for neighborhood in yelp_location["neighborhoods"]:
            db_neighborhood = YelpNeighborhood.get(neighborhood)
            if not db_neighborhood:
                db_neighborhood = YelpNeighborhood.create(neighborhood)
            if db_neighborhood:
                o.neighborhoods.add(db_neighborhood)

        o.save()
        return o
                
    @staticmethod
    def exists(yelp_location):
        return YelpLocation.get(yelp_location) != None
    
    @staticmethod
    def get(yelp_location):
        locations = YelpLocation.objects.filter(city = yelp_location["city"],
                                           display_address = yelp_location["display_address"],
                                           geo_accuracy = yelp_location["geo_accuracy"],
                                           postal_code = yelp_location["postal_code"],
                                           country_code = yelp_location["country_code"],
                                           address = yelp_location["address"],
                                           state_code = yelp_location["state_code"],
                                           #coordinate = yelp_location["coordinate"]
                                           )
        if len(locations) > 0:
            return locations[0]
        return None

    @staticmethod
    def get_or_create(yelp_location):
        location = YelpLocation.get(yelp_location)
        if not location:
            location = YelpLocation.create(yelp_location)
            
        return location

class YelpActivity(DbObject):
    yelp_id = models.CharField(unique=True, max_length=128)
    rating = models.FloatField(default = 3)
    review_count = models.IntegerField(default = 0)
    phone = models.CharField(max_length=32)
    display_phone = models.CharField(max_length=32)
    snippet_text = models.TextField(max_length = 512)
    categories = models.ManyToManyField(YelpCategory)
    location = models.ForeignKey(YelpLocation)
    
    @staticmethod
    def create(yelp_business):
        if YelpActivity.exists(yelp_business):
            raise Exception("This activity already exists in the database")
        
        o = YelpActivity()
        o.name = yelp_business["name"]
        o.yelp_id = yelp_business["id"]
        o.rating = yelp_business["rating"]
        o.review_count = yelp_business["review_count"]
        o.phone = yelp_business["phone"]
        o.display_phone = yelp_business["display_phone"]
        o.snippet_text = yelp_business["snippet_text"]
        
        #adds location to database
        db_location = YelpLocation.get(yelp_business["location"])
        print db_location
        if not db_location:
            print db_location
            db_location = YelpLocation.create(yelp_business["location"])
        
        if db_location:
            o.location = db_location

        o.save()

        # adds categories to database
        for category in yelp_business["categories"]:
            print category
            db_category = YelpCategory.get(category)
            print db_category
            if not db_category:
                print "creating category"
                db_category = YelpCategory.create(category)
                print db_category
            if db_category:
                o.categories.add(db_category)

        o.save()
        return o
            
    @staticmethod
    def exists(yelp_business):
        return YelpActivity.objects.filter(yelp_id = yelp_business["id"]).exists()
    
    @staticmethod
    def get(yelp_business):
        activities = YelpActivity.objects.filter(yelp_id = yelp_business["id"])
        
        if len(activities) > 0:
            return activities[0]
        return None
    
    @staticmethod
    def get_or_create(yelp_business):
        activity = YelpActivity.get(yelp_business)
        if not activity:
            activity = YelpActivity.create(yelp_business)
            
        return activity
            
        

class User(DbObject):
    username = models.CharField(max_length=200, unique=True)
    
    def __unicode__(self):
        return "username: " + self.username + " name: " + self.name
    
class Tag(DbObject):
    user = models.ForeignKey(User)

class Activity(DbObject):
    yelp_activity = models.ForeignKey(YelpActivity, unique=True)
    
    @staticmethod
    def get_or_create(yelp_activity):
        activity = None
        try:
            activity = Activity.objects.get(yelp_activity=yelp_activity)
        except Activity.DoesNotExist:
            activity = Activity(yelp_activity=yelp_activity)
            activity.name = yelp_activity.name
            activity.save()
            
        return activity

class Trip(DbObject):
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    duration = models.IntegerField(default=7)
    user = models.ForeignKey(User)

class TripActivity(DbObject):
    activity = models.ForeignKey(Activity)
    trip = models.ForeignKey(Trip)
    tags = models.ManyToManyField(Tag, blank=True)
    
    @staticmethod
    def get_or_create(activity, trip):
        trip_activity = None
        try:
            trip_activity = TripActivity.objects.get(activity=activity, trip=trip)
        except TripActivity.DoesNotExist:
            trip_activity = TripActivity(activity=activity, trip=trip)
            trip_activity.name = activity.name
            trip_activity.save()
            
        return trip_activity

