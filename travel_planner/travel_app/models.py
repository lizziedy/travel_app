from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
import datetime
import sys

class TravelAppDatabaseException(Exception):
    pass

# Create your models here.

class ImmutableObject(models.Model):
    def __setattr__(self, name, value):
        if self._can_edit(name, value):
            super(ImmutableObject, self).__setattr__(name, value)
        else:
            raise TravelAppDatabaseException("You cannot edit " + name)
    
    def _can_edit(self, name, value):
        return True
    
    class Meta:
        abstract = True

class DbObject(ImmutableObject):
    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    
    class Meta:
        abstract = True

class Coordinate(ImmutableObject):
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

class Category(ImmutableObject):
    name = models.CharField(max_length=128)
    search_name = models.CharField(max_length=128, unique=True)
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
    

class Neighborhood(ImmutableObject):
    name = models.CharField(max_length=128)

    @staticmethod
    def create(yelp_neighborhood):
        if Neighborhood.get(yelp_neighborhood) is not None:
            raise Exception("This neighborhood already exists in the database")
        
        o = Neighborhood()
        o.name = yelp_neighborhood
        print "saving neighborhood"
        o.save()
        print "saved neighborhood"
        return o
        
    @staticmethod
    def get(yelp_neighborhood):
        neighborhoods = Neighborhood.objects.filter(name = yelp_neighborhood)
        if len(neighborhoods) > 0:
            return neighborhoods[0] 
        return None 

    @staticmethod
    def get_or_create(yelp_neighborhood):
        print "in neighborhood get_or_create"
        neighborhood = Neighborhood.get(yelp_neighborhood)
        print "neighborhood get returned: " + str(neighborhood)
        if neighborhood is None:
            neighborhood = Neighborhood.create(yelp_neighborhood)
            
        return neighborhood

class CountryCode(ImmutableObject):
    code = models.CharField(max_length=8)
    
    @staticmethod
    def get_or_create(country_code):
        codes = CountryCode.objects.filter(code=country_code)
        if len(codes) > 0:
            return codes[0]
        
        code = CountryCode(code=country_code)
        code.save()
        return code

class StateCode(ImmutableObject):
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
         

class Location(ImmutableObject):
    country_code = models.ForeignKey(CountryCode)
    state_code = models.ForeignKey(StateCode, blank=True, null=True)
    city = models.CharField(max_length=128, blank=True)
    display_address = models.CharField(max_length=512, blank=True)
    neighborhoods = models.ManyToManyField(Neighborhood, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=512, blank=True)
    coordinate = models.ForeignKey(Coordinate, blank=True, null=True)

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
        
        country_code = CountryCode.get_or_create(yelp_location["country_code"])
        o.country_code = country_code
        if "state_code" in yelp_location:
            o.statecode = StateCode.get_or_create(yelp_location["state_code"], country_code)

        o.save()

        # adds categories to database
        if "neighborhoods" in yelp_location:
            for neighborhood in yelp_location["neighborhoods"]:
                db_neighborhood = Neighborhood.get_or_create(neighborhood)
                if db_neighborhood is not None:
                    o.neighborhoods.add(db_neighborhood)

        o.save()
        return o
                
    @staticmethod
    def yelp_get(yelp_location):
        country_code = None
        state_code = None
        coordinate = None
        try:
            country_code = CountryCode.objects.get(yelp_location["country_code"])
            state_code = StateCode.objects.get(yelp_location["state_code"])
            coordinate = Coordinate.yelp_get(yelp_location["coordinate"])
        except:
            pass
        
        locations = Location.objects.filter(city = yelp_location["city"],
                                           display_address = yelp_location["display_address"],
                                           postal_code = yelp_location["postal_code"],
                                           address = yelp_location["address"],
                                           country_code = country_code,
                                           state_code =state_code,
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
    
class ActivitySource(ImmutableObject):
    yelp_id = models.CharField(unique=True, null=True, default=None, max_length=128)
    user = models.ForeignKey("User", null=True, default=None)
    
    def save(self, *args, **kwargs):
        # only save the first time
        print "SAVE ACTVITIYSOURCE"
        print self.id
        if self.id is None:
            super(ActivitySource, self).save(*args, **kwargs)


class Activity(DbObject):
    activitysource = models.OneToOneField(ActivitySource)
    rating = models.FloatField(null=True, default=None)
    review_count = models.IntegerField(default = 0)
    phone = models.CharField(max_length=32, blank=True)
    display_phone = models.CharField(max_length=32, blank=True)
    description = models.TextField(max_length = 1024, blank=True)
    categories = models.ManyToManyField(Category)
    location = models.ForeignKey(Location)
    
    yelp_dependencies = ["rating", "review_count", "phone", 
                         "display_phone", "categories", "location",
                         "name"]
    
    def __unicode__(self):
        ret_str = "[" + str(self.id) + "] " + self.name
        if self.activitysource.yelp_id is not None:
            ret_str += " (YELP)"
        elif self.activitysource.user is not None:
            ret_str += " (" + str(self.activitysource.user) + ")"

        return ret_str
    
    def _can_edit(self, name, value):
        """
        can't edit if trying to edit activitysource and it already exists or
        if you're trying to edit a yelp dependent value and the activity is
        a yelp activity.
        """
        if name == "activitysource":
            try:
                getattr(self, name)
            except:
                return True
            return False
        elif name in self.yelp_dependencies:
            try:
                getattr(self, name)
            except:
                return True
            try:
                if self.activitysource.yelp_id is not None:
                    return False
            except:
                return True

        return True
    
    def rating_str(self):
        rating = ""
        for _ in range(int(self.rating)):
            rating += "*"
        if int(self.rating) < self.rating:
            rating += "."

        return rating
    
    def details(self):
        det_str = ""
        
        det_str += self.name
        if self.rating is not None:
            det_str += " " + self.rating_str() + " (" + str(self.review_count) + ")"
        det_str += "\n"
        det_str += "phone: "
        if self.display_phone is not None:
            det_str += self.display_phone
        elif self.phone is not None:
            det_str += self.phone
        det_str += "\n"
        det_str += "categories: "
        # TODO:
        det_str += "\n"
        det_str += "description:\n" + self.description + "\n"
        det_str += "location: "
        # TODO:
        
        return det_str
    
    @staticmethod
    def yelp_create(yelp_business):
        if Activity.yelp_get(yelp_business) is not None:
            raise Exception("This activity already exists in the database")
        
        o = Activity()
        
        o.name = yelp_business["name"]
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

        # TODO: better
        activitysource = ActivitySource(yelp_id=yelp_business["id"])
        activitysource.save()
        print activitysource
        print activitysource.id
        o.activitysource = activitysource

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
        activity_sources = ActivitySource.objects.filter(yelp_id = yelp_business["id"])
        print activity_sources
        if len(activity_sources) > 0:
            activities = Activity.objects.filter(activitysource=activity_sources[0])
            print activities
            if len(activities) > 0:
                return activities[0]
            
        return None
    
    @staticmethod
    def yelp_get_or_create(yelp_business):
        activity = Activity.yelp_get(yelp_business)
        if activity is None:
            activity = Activity.yelp_create(yelp_business)
            
        return activity


            
class User(DbObject):
    username = models.CharField(max_length=200, unique=True)
    
    def __unicode__(self):
        return "username: " + self.username + " name: " + self.name
    
class Tag(DbObject):
    user = models.ForeignKey(User)

"""
class ActivitySeason(ImmutableObject):
    activity = models.ForeignKey(Activity)
    name = models.CharField(max_length=256)
    season_start = models.DateField(blank=True, null=True, default=None)
    season_end = models.DateField(blank=True, null=True, default=None)

class ActivityHours(models.Model):
    season = models.ForeignKey(ActivitySeason)
    day_of_week = models.IntegerField() #monday 0, sunday 6
    
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


class Day(ImmutableObject):
    date = models.DateField(blank=True, null=True)
    order = models.IntegerField()
    trip = models.ForeignKey(Trip)
    comments = models.TextField(max_length="1024", blank=True)
    
    
class TimeInterval(ImmutableObject):
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
            ret_str += "(" + str(self.priority) + ") "
        ret_str += "[" + str(self.id) + "] " + self.name
        tag_str = self.tag_list_str()
        if len(tag_str) > 0:
            ret_str += " (" + tag_str + ")"
        return ret_str
    
    def tag_list_str(self):
        ret_str = ""
        if len(self.tags.all()) > 0:
            for tag in self.tags.all():
                ret_str += tag.name + ", "
            ret_str = ret_str[:-2]
        return ret_str
    
    def details(self):
        det_str = ""
        
        det_str += self.name + "\n"
        det_str += "priority: " + str(self.priority) + "\n"
        det_str += "tags: " + self.tag_list_str() + "\n"
        det_str += "comments: " + self.comments + "\n"
        det_str += "\nactivity:\n"
        det_str += self.activity.details()
        
        return det_str
    
    class Meta:
        ordering = ["priority", "name"]
        
        
@receiver(post_delete)
def post_delete(sender, **kwargs):
    if sender is Activity:
        instance = kwargs['instance']
        activitysource = instance.activitysource
        activitysource.delete()
        
        