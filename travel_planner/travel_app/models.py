from django.db import models
import datetime
import sys

class TravelAppDatabaseException(Exception):
    pass

# Create your models here.

class DbObject(models.Model):
    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)
    immutable_fields = []
    
    def __setattr__(self, name, value):
        id_ = getattr(self, "id", None)
        if id_ is not None:
            if name in self.immutable_fields:
                raise TravelAppDatabaseException("This field cannot be changed.") 
        super(DbObject, self).__setattr__(name, value)    
    
    class Meta:
        abstract = True

class Coordinate(models.Model):
    latitude = models.DecimalField(max_digits=48, decimal_places = 32)
    longitude = models.DecimalField(max_digits=48, decimal_places = 32)

    
    @staticmethod
    def yelp_create(yelp_coordinate):
        if Coordinate.yelp_get(yelp_coordinate) is not None:
            raise Exception("This coordinate already exists in the database")

        o = Coordinate()
        o.latitude = yelp_coordinate["latitude"]
        o.longitude = yelp_coordinate["longitude"]
        o.save()
        return o

    @staticmethod
    def yelp_get(yelp_coordinate):
        coordinates = Coordinate.objects.filter(latitude=yelp_coordinate["latitude"], 
                                               longitude=yelp_coordinate["longitude"])
        
        if len(coordinates) > 0:
            return coordinates[0]
        return None

    @staticmethod
    def yelp_get_or_create(yelp_coordinate):
        coordinate = Coordinate.yelp_get(yelp_coordinate)
        if coordinate is None:
            coordinate = Coordinate.yelp_create(yelp_coordinate)
            
        return coordinate

class Category(models.Model):
    name = models.CharField(max_length=128)
    search_name = models.CharField(max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, default=None)
    
    @staticmethod
    def yelp_create(yelp_category):
        if Category.yelp_get(yelp_category) is not None:
            raise Exception("This category already exists in the database")

        o = Category()
        o.name = yelp_category[0]
        o.search_name = yelp_category[1]
        o.save()
        return o

    @staticmethod
    def yelp_get(yelp_category):
        categories = Category.objects.filter(name=yelp_category[0],
                                             search_name=yelp_category[1])
        
        if len(categories) > 0:
            return categories[0]
        return None

    @staticmethod
    def yelp_get_or_create(yelp_category):
        category = Category.yelp_get(yelp_category)
        if category is None:
            category = Category.yelp_create(yelp_category)
            
        return category
    

class Neighborhood(models.Model):
    name = models.CharField(max_length=128)

    @staticmethod
    def yelp_create(yelp_neighborhood):
        if Neighborhood.yelp_get(yelp_neighborhood) is not None:
            raise Exception("This neighborhood already exists in the database")
        
        o = Neighborhood()
        o.name = yelp_neighborhood
        o.save()
        
    @staticmethod
    def yelp_get(yelp_neighborhood):
        neighborhoods = Neighborhood.objects.filter(name = yelp_neighborhood)
        if len(neighborhoods) > 0:
            return neighborhoods[0] 
        return None 

    @staticmethod
    def yelp_get_or_create(yelp_neighborhood):
        neighborhood = Neighborhood.yelp_get(yelp_neighborhood)
        if neighborhood is not None:
            neighborhood = Neighborhood.yelp_create(yelp_neighborhood)
            
        return neighborhood

class CountryCode(models.Model):
    code = models.CharField(max_length=8)
    
    @staticmethod
    def get_or_create(country_code):
        codes = CountryCode.objects.filter(code=country_code)
        if len(codes) > 0:
            return codes[0]
        
        code = CountryCode(code=country_code)
        code.save()
        return code

class StateCode(models.Model):
    code = models.CharField(max_length=8)
    country_code = models.ForeignKey(CountryCode)
    
    @staticmethod
    def get_or_create(state_code, country_code):
        codes = StateCode.objects.filter(code=state_code, 
                                         country_code=country_code)
        if len(codes) > 0:
            return codes[0]
        
        code = StateCode(code=state_code, country_code=country_code)
        code.save()
        return code
         

class Location(models.Model):
    country_codes = models.ManyToManyField(CountryCode)
    state_codes = models.ManyToManyField(StateCode, blank=True)
    city = models.CharField(max_length=128, blank=True)
    display_address = models.CharField(max_length=512, blank=True)
    neighborhoods = models.ManyToManyField(Neighborhood, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=512, blank=True)
    coordinate = models.ForeignKey(Coordinate, blank=True)

    @staticmethod
    def yelp_create(yelp_location):
        if Location.yelp_get(yelp_location) is not None:
            raise Exception("This location already exists in the database")

        o = Location()        
        o.city = yelp_location["city"]
        o.display_address = yelp_location["display_address"]
        o.postal_code = yelp_location["postal_code"]
        o.address = yelp_location["address"]

        db_coordinate = Coordinate.yelp_get_or_create(yelp_location["coordinate"])
        o.coordinate = db_coordinate
        
        o.save()

        country_code = CountryCode.get_or_create(yelp_location["country_code"])
        o.country_codes.add(country_code)
        if "state_code" in yelp_location:
            o.state_codes.add(StateCode.get_or_create(yelp_location["state_code"], country_code))

        # adds categories to database
        if "neighborhoods" in yelp_location:
            for neighborhood in yelp_location["neighborhoods"]:
                db_neighborhood = Neighborhood.yelp_get_or_create(neighborhood)
                if db_neighborhood is not None:
                    o.neighborhoods.add(db_neighborhood)

        o.save()
        return o
                
    @staticmethod
    def yelp_get(yelp_location):
        country_code = None
        state_code = None
        try:
            country_code = CountryCode.objects.get(yelp_location["country_code"])
            state_code = StateCode.objects.get(yelp_location["state_code"])
        except:
            pass
        coordinate = Coordinate.yelp_get(yelp_location["coordinate"])
        
        locations = Location.objects.filter(city = yelp_location["city"],
                                           display_address = yelp_location["display_address"],
                                           postal_code = yelp_location["postal_code"],
                                           address = yelp_location["address"],
                                           country_codes__in=[country_code],
                                           state_codes__in=[state_code],
                                           coordinate=coordinate
                                           )
        if len(locations) > 0:
            return locations[0]
        return None

    @staticmethod
    def yelp_get_or_create(yelp_location):
        location = Location.yelp_get(yelp_location)
        if location is None:
            location = Location.yelp_create(yelp_location)
            
        return location

class Activity(DbObject):
    yelp_id = models.CharField(unique=True, null=True, default=None, max_length=128)
    user = models.ForeignKey("User", null=True, default=None)
    rating = models.FloatField(null=True, default=None)
    review_count = models.IntegerField(default = 0)
    phone = models.CharField(max_length=32, blank=True)
    display_phone = models.CharField(max_length=32, blank=True)
    description = models.TextField(max_length = 1024, blank=True)
    categories = models.ManyToManyField(Category)
    location = models.ForeignKey(Location)
    
    immutable_fields = ["yelp_id", "user"]
    
    @staticmethod
    def yelp_create(yelp_business):
        if Activity.yelp_get(yelp_business) is not None:
            raise Exception("This activity already exists in the database")
        
        o = Activity()
        o.name = yelp_business["name"]
        o.yelp_id = yelp_business["id"]
        o.rating = yelp_business["rating"]
        o.review_count = yelp_business["review_count"]
        
        if "snippet_text" in yelp_business:
            o.description = yelp_business["snippet_text"]
        if "phone" in yelp_business:        
            o.phone = yelp_business["phone"]
        if "display_phone" in yelp_business:
            o.display_phone = yelp_business["display_phone"]
            
        #adds location to database
        if "location" in yelp_business:
            db_location = Location.yelp_get_or_create(yelp_business["location"])
            o.location = db_location

        o.save()

        # adds categories to database
        if "categories" in yelp_business:
            for category in yelp_business["categories"]:
                db_category = Category.yelp_get_or_create(category)
                o.categories.add(db_category)

        o.save()
        return o
            
    @staticmethod
    def yelp_get(yelp_business):
        activities = Activity.objects.filter(yelp_id = yelp_business["id"])
        
        if len(activities) > 0:
            return activities[0]
        return None
    
    @staticmethod
    def yelp_get_or_create(yelp_business):
        activity = Activity.yelp_get(yelp_business)
        if not activity:
            activity = Activity.yelp_create(yelp_business)
            
        return activity
            


class User(DbObject):
    username = models.CharField(max_length=200, unique=True)
    
    def __unicode__(self):
        return "username: " + self.username + " name: " + self.name
    
class Tag(DbObject):
    user = models.ForeignKey(User)

"""
class ActivityHours(models.Model):
    activity = models.ForeignKey(Activity)
    season_start = models.DateField(blank=True, null=True, default=None)
    season_end = models.DateField(blank=True, null=True, default=None)
    day_of_week = models.IntegerField()
    
class ActivityHoursTimeInterval(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    activity_hours = models.ForeignKey(ActivityHours)
"""

class Trip(DbObject):
    start_date = models.DateField(blank=True, null=True)
    duration = models.IntegerField(default=7)
    user = models.ForeignKey(User)
    comments = models.TextField(max_length="1024", blank=True)
    
    def save(self, *args, **kwargs):
        super(Trip, self).save(*args, **kwargs)

        current_num_days = len(self.day_set.all())
        if self.duration < current_num_days:
            for _ in range(self.duration, current_num_days):
                self.day_set.all()[len(self.day_set.all())-1].delete()
        elif self.duration > current_num_days:
            for day_num in range(current_num_days, self.duration):
                day = Day(order=day_num + 1, trip=self)
                day.save()
        
        if self.start_date is not None:
            for day_num in range(self.duration): 
                day = self.day_set.all()[day_num]
                day.date = self.start_date + datetime.timedelta(days=day_num)
                day.save()
                
    def __unicode__(self):
        print_str = self.name
        if self.start_date is not None:
            print_str += " (" + str(self.start_date) + " - " + str(self.start_date + datetime.timedelta(days=self.duration)) + ")"
        else:
            print_str += " for " + str(self.duration) + " days"
        return print_str 


class Day(models.Model):
    date = models.DateField(blank=True, null=True)
    order = models.IntegerField()
    trip = models.ForeignKey(Trip)
    comments = models.TextField(max_length="1024", blank=True)
    
    
class TimeInterval(models.Model):
    start_time = models.TimeField(blank=True, null=True, default=None)
    end_time = models.TimeField(blank=True, null=True, default=None)
    activity = models.ForeignKey('TripActivity')
    day = models.ForeignKey(Day)

class TripActivity(DbObject):
    activity = models.ForeignKey(Activity)
    trip = models.ForeignKey(Trip)
    tags = models.ManyToManyField(Tag, blank=True)
    priority = models.IntegerField(default = sys.maxint)
    comments = models.TextField(max_length="1024", blank=True)
    
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
    
    def __unicode__(self):
        ret_str = ""
        if self.priority != sys.maxint:
            ret_str += "(" + str(self.priority) + ")"
        ret_str += " [" + str(self.id) + "] " + self.name
        if len(self.tags.all()) > 0:
            ret_str += " ("
            for tag in self.tags.all():
                ret_str += tag.name + ", "
            ret_str = ret_str[:-2]
            ret_str += ")"
        return ret_str
    
    class Meta:
        ordering = ["priority", "name"]
        
        
        
        
        
        