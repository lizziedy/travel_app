import models
import cmd
import django.db
import re
import requester
import datetime
import sys
from operator import attrgetter
from decimal import Decimal
import copy

class TravelAppException(Exception):
    """ An exception for a travel app """

class TravelApp:
    current_user = None
    current_trip = None
    current_search = None
    current_activities = None
    
    letter_regex = re.compile("^[a-zA-Z]")
    
    @staticmethod
    def check_tag_name(tagname):
        if "(" in tagname or ")" in tagname:
            raise TravelAppException("( and ) are not legal characters in a tag name")
        if "," in tagname:
            raise TravelAppException(", is not a legal character in a tag name")
        
        tagname_split = tagname.split(" ")
        for partial in tagname_split:
            if partial == "AND":
                raise TravelAppException("AND cannot be a component of a tag name (use 'and' instead)")
            if partial == "OR":
                raise TravelAppException("OR cannot be a component of a tag name (use 'or' instead)")
    
    def search(self, category_filter = None,
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
        try:
            result = requester.get_yelp_request(category_filter, location, term, limit, offset, sort, radius_filter, deals_filter, cc, lang, bounds, ll, cll)
        except Exception as e:
            raise TravelAppException(str(e))
        self.current_search = result
        return result
    
    def pretty_string_business(self, business):
        num_rating = business["rating"]
        rating = ""
        for _ in range(int(num_rating)):
            rating += "*"
        if int(num_rating) < num_rating:
            rating += "."
        
        return rating + "\t" + business["name"] + " " + \
              " (number of reviews: " + \
              str(business['review_count']) + ")"
    
    def login(self, username):
        if self.current_user:
            raise TravelAppException("A user is already logged in. Please logout.")
        
        try:
            self.current_user = models.User.objects.get(username=username)
        except models.User.DoesNotExist:
            raise TravelAppException("The user does not yet exist. Please create the user.")
        
        print "You have successfully logged in as " + str(self.current_user)
        
    def logout(self):
        user = self.current_user
        self.current_user = None
        self.current_trip = None
        self.current_search = None
        self.current_activities = None
        
        print "You have successfully logged out from " + str(user)
    
    def create_user(self, username, name):
        user = models.User(name=name, username = username)
                
        try:
            user.save()
            print "You have successfully saved the user " + str(user)
        except django.db.IntegrityError:
            raise TravelAppException("A user already exists with that username. Please try another.")
        
    def create_tag(self, name):
        TravelApp.check_tag_name(name)
        self.create_generic(name, models.Tag)        
         
    def create_trip(self, name, start_date=None, duration=None):
        trip = self.create_generic(name, models.Trip)
        
        if start_date is not None:
            try:
                date_split = start_date.split("-")
                year = int(date_split[0])
                month = int(date_split[1])
                day = int(date_split[2])
            except:
                raise TravelAppException("The start date was not formatted correctly (yyyy-mm-dd)")
            
            try:
                date = datetime.date(year, month, day)
            except Exception as e:
                raise TravelAppException(str(e))
            
            trip.start_date = date
            
        if duration is not None:
            try:
                duration = int(duration)
            except:
                raise TravelAppException("The duration of the trip must be an integer value.")
            
            trip.duration = duration
            
        trip.save()
        
        print "You have successfully saved the trip " + str(trip)
        
    def create_activity(self, name, country_code, public=False):
        activity = models.Activity(name=name)

        country_code = models.CountryCode.get_or_create(country_code)

        location = models.Location()
        location.country_code = country_code
        location.save()
        activity.location = location
        
        activitysource = models.ActivitySource()
        activitysource.yelp_id = None
        if public:
            activitysource.user = None
        else:
            if not self.current_user:
                raise TravelAppException("You must be logged in to add this. Please login.")
            activitysource.user = self.current_user
        activitysource.save()
        activity.activitysource = activitysource
            
        activity.save()
        
    def create_generic(self, name, model_class): 
        if not self.current_user:
            raise TravelAppException("You must be logged in to add this. Please login.")
        if not self.letter_regex.match(name):
            raise TravelAppException("You must start the name with a letter.")
        # want to ensure uniqueness
        try:
            model_class.objects.get(name=name, user = self.current_user)
            raise TravelAppException("This name already exists. The name must be unique.")
        except model_class.DoesNotExist:
            pass
        
        item = model_class(name=name, user=self.current_user)
        item.save()
        
        return item

    def edit_trip(self, name, start_date=None, duration=None, new_name=None):
        trip = self.get_trip(name)
        
        if start_date is not None:
            print "in date"
            try:
                date_split = start_date.split("-")
                year = int(date_split[0])
                month = int(date_split[1])
                day = int(date_split[2])
            except:
                raise TravelAppException("The start date was not formatted correctly (yyyy-mm-dd)")
            
            try:
                date = datetime.date(year, month, day)
            except Exception as e:
                raise TravelAppException(str(e))
            
            trip.start_date = date
            
        if duration is not None:
            print "in duration"
            try:
                duration = int(duration)
            except:
                raise TravelAppException("The duration of the trip must be an integer value.")
            
            print trip.duration
            trip.duration = duration
            print trip.duration
            
        if new_name is not None:
            print "in name"
            trip.name = new_name
            
        trip.save()
        
        print "You have successfully saved the trip " + str(trip)

    def edit_global_activity_location(self,
                                      activity_id,
                                      country_code = None,
                                      state_code = None,
                                      city = None,
                                      display_address = None,
                                      address = None,
                                      neighborhoods = None,
                                      postal_code = None,
                                      coordinate = None):
        try:
            activity_id = int(activity_id)
        except:
            raise TravelAppException("The activity id must be an integer")
        
        activity = models.Activity.objects.get(id=activity_id)
        
        if activity.activitysource.user is not None and activity.activitysource.user != self.current_user:
            raise TravelAppException("You do not have permission to edit this activity")

        location = activity.location
        
        try:
            if country_code is not None:
                country_code = models.CountryCode.get_or_create(country_code)
                location.country_code = country_code
            if state_code is not None:
                if country_code is None:
                    country_code = location.country_code
                state_code = models.StateCode.get_or_create(state_code, country_code)
                location.state_code = state_code
            if city is not None:
                location.city = city
            if address is not None:
                location.address = address
                if display_address is None:
                    location.display_address = address
            if display_address is not None:
                if location.address is None:
                    location.address = display_address
                location.display_address = display_address
            if neighborhoods is not None:
                location.neighborhoods.clear()
                for neighborhood in neighborhoods:
                    neighborhood = models.Neighborhood.get_or_create(neighborhood)
                    print neighborhood
                    print neighborhood.name
                    print neighborhood.id
                    location.neighborhoods.add(neighborhood)
            if postal_code is not None:
                location.postal_code = postal_code
            if coordinate is not None:
                coord_err_str = "coordinate should be formatted as <latitude longitude>"
                coordinate_split = coordinate.split(" ")
                if len(coordinate_split) != 2:
                    raise TravelAppException(coord_err_str)
                try:
                    latitude = Decimal(coordinate_split[0])
                    longitude = Decimal(coordinate_split[1])
                except:
                    raise TravelAppException("latitude and longitude must both be floats") 

                coordinate = models.Coordinate(latitude=latitude, longitude=longitude)
                coordinate.save()
                location.coordinate = coordinate
                
            location.save()
        except models.TravelAppDatabaseException as e:
            raise TravelAppException(str(e))

    def edit_global_activity(self, activity_id, rating = None, 
                             review_count = None, phone = None, 
                             description = None, name=None):
        try:
            activity_id = int(activity_id)
        except:
            raise TravelAppException("The activity id must be an integer")
        
        activity = models.Activity.objects.get(id=activity_id)
        
        if activity.activitysource.user is not None and activity.activitysource.user != self.current_user:
            raise TravelAppException("You do not have permission to edit this activity")

        try:
            if rating is not None:
                try:
                    rating = float(rating)
                except:
                    raise TravelAppException("The rating must be a float value")
                activity.rating = rating
                
            if review_count is not None:
                try:
                    review_count = int(review_count)
                except:
                    raise TravelAppException("The review count must be an integer")
                activity.review_count = review_count
                
            if phone is not None:
                phone_split = phone.split(" ")
                activity.phone = phone_split[0]
                if len(phone_split) > 1:
                    activity.display_phone = " ".join(phone_split[1:])
                else:
                    activity.display_phone = activity.phone
            
            if name is not None:
                activity.name = name
            
            if description is not None:
                activity.description = description
        except models.TravelAppDatabaseException as e:
            raise TravelAppException(str(e))
            
        activity.save()
        

    def goto(self, trip):
        trip = self.get_trip(trip)
        self.current_trip = trip
        
    def leave(self):
        self.current_trip = None
        self.current_activities = None
          
    def get_generic(self, identifier, model_class):
        if not self.current_user:
            raise TravelAppException("You must be logged in to add a tag. Please login.")
        
        item = None
        try:
            if self.letter_regex.match(identifier):
                item = model_class.objects.get(name=identifier, user=self.current_user)
            else:
                item = model_class.objects.get(id=int(identifier))
        except model_class.DoesNotExist:
            raise TravelAppException("The item " + str(identifier) + " does not exist")
            
        return item
    
    def get_tag(self, identifier):
        return self.get_generic(identifier, models.Tag)
    
    def get_trip(self, identifier):
        return self.get_generic(identifier, models.Trip)

    def get_activity(self, identifier): 
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to get activities. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to get activities. Please goto a trip.")

        try:
            db_activity = models.TripActivity.objects.get(id = identifier, trip=self.current_trip) 
        except models.TripActivity.DoesNotExist:
            raise TravelAppException("The activity with id " + str(identifier) + " does not exist in trip " + self.current_trip)
        
        return db_activity
   
    def get_day(self, day):
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to get a day. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to get a day. Please goto a trip.")
        
        try:
            order = int(day)
        except Exception as e:
            print str(e)
            raise TravelAppException("You must enter the day number of your trip, not the date itself.")
   
        try:
            db_day = models.Day.objects.get(order=order, trip=self.current_trip)
        except models.Day.DoesNotExist:
            raise TravelAppException("The day with order " + str(order) + " does not exist in trip " + self.current_trip)
        
        return db_day
   
    def get_generics(self, model_class):
        if not self.current_user:
            raise TravelAppException("You must be logged in to get objects. Please login.")

        return model_class.objects.filter(user = self.current_user)
        
    def get_tags(self):
        return self.get_generics(models.Tag)

    def get_trips(self):
        return self.get_generics(models.Trip)
    
    def get_days(self):
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to get days. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to get days. Please goto a trip.")

        return models.Day.objects.filter(trip = self.current_trip)
    
    def get_global_activities(self):
        activities = models.Activity.objects.all()
        ret_activities = []
        
        for activity in activities:
            if activity.activitysource.user is None or activity.activitysource.user == self.current_user:
                ret_activities.append(activity)
            
        return ret_activities
    
    def delete_generic(self, identifier, model_class):
        item = self.get_generic(identifier, model_class)
            
        if item:
            item_name = item.name
            item_id = item.id
            item.delete()
            print "You have successfully deleted \"" + item_name + "\" with id [" + str(item_id) + "]" 
    
    def delete_tag(self, identifier):
        self.delete_generic(identifier, models.Tag)
    
    def delete_trip(self, identifier):
        self.delete_generic(identifier, models.Trip)
        
    def delete_activity(self, identifier):
        self.delete_generic(identifier, models.TripActivity)
        
    def add_activity(self, index):
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to add an activity. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to add an activity. Please goto a trip.")
        if self.current_search is None or len(self.current_search) == 0:
            raise TravelAppException("Try another search. There are no activities in the cache.")
        try:
            index = int(index)
        except:
            raise TravelAppException("The index must be an integer value")
        if index >= len(self.current_search):
            raise TravelAppException("The index you have used is out of range")
        activity = self.current_search[index]
        db_activity = models.Activity.yelp_get_or_create(activity)
        db_trip_activity = models.TripActivity.get_or_create(activity=db_activity, 
                                                             trip=self.current_trip)
        
        print "You have successfully added activity " + str(db_trip_activity) + " to trip " + str(self.current_trip)
        
    def tag_activity(self, activity_id, tagname_or_id, force = False):
        tag = None
        activity = -1
        
        try:
            tag = self.get_tag(tagname_or_id)
        except models.Tag.DoesNotExist:
            if force:
                pass
            else:
                raise TravelAppException("the given tag does not exist. To create a tag, use the force option.")

        try:
            activity_id = int(activity_id)
        except Exception:
            raise TravelAppException("the activity identifier must be an integer")

        try:
            activity = self.get_activity(activity_id)
        except models.TripActivity.DoesNotExist:
            raise TravelAppException("the given activity does not exist.")
        
        if activity > -1 and tag is not None:
            activity.tags.add(tag)
            activity.save()
        
    def untag_activity(self, activity_id, tagname_or_id):
        tag = None
        activity = -1
        
        try:
            tag = self.get_tag(tagname_or_id)
        except models.Tag.DoesNotExist:
            raise TravelAppException("the given tag does not exist. To create a tag, use the force option.")

        try:
            activity_id = int(activity_id)
        except Exception:
            raise TravelAppException("the activity identifier must be an integer")

        try:
            activity = self.get_activity(activity_id)
        except models.TripActivity.DoesNotExist:
            raise TravelAppException("the given activity does not exist.")
        
        if activity > -1 and tag is not None:
            activity.tags.remove(tag)
            activity.save()
    
    def order(self, activity_ids):
        if self.current_activities is None:
            self.get_activities()
            
        all_activities = self._get_activities()
        
        ordered_activities = []
        for activity_id in activity_ids:
            found = False
            for activity in self.current_activities:
                if activity.id == activity_id:
                    found = True
                    ordered_activities.append(activity)
                    break
            if not found:
                raise TravelAppException("The activity id " + str(activity_id) + " does not exist in the current list of activities.")
        all_ordered_activities = copy.deepcopy(ordered_activities)
            
        # ensure we don't end up sorting unsorted activities accidentally
        sortable_activities = []
        for activity in all_activities:
            print activity
            if activity.priority != sys.maxint or activity in self.current_activities:
                print "\tadded"
                sortable_activities.append(activity)
            
        # reorder the activities in the sortable activities
        for i in range(len(sortable_activities)):
            activity = sortable_activities[i]
            if activity in all_ordered_activities:
                print "len(sortable_activities): " + str(len(sortable_activities))
                print "len(ordered_activities): " + str(len(ordered_activities))
                print "i: " + str(i)
                sortable_activities[i] = ordered_activities[0]
                ordered_activities = ordered_activities[1:]
        
        # go through sortable activities and reassign priorities
        for i in range(len(sortable_activities)):
            activity = sortable_activities[i]
            activity.priority = i+1
            activity.save()
            
        self.current_activities = sorted(self.current_activities, key=attrgetter('priority', 'name'))
        return self.current_activities
    
    def get_activities(self, tags = None, tags_operator = "AND", days = None):
        activities = self._get_activities()
         
        final_list = []
        
        if tags is not None:
            split_tags = tags.split(",")
            tmp_tags = []
            for tag in split_tags:
                self.check_tag_name(tag)
                tag = tag.strip()
                tmp_tags.append(tag)
                
            split_tags = tmp_tags
            
            for activity in activities:
                if tags_operator == "AND":
                    fits = True
                elif tags_operator == "OR":
                    fits = False
                else:
                    raise TravelAppException("The only allowed tag operators are AND and OR")
                
                for tag in split_tags:
                    try:
                        tag = self.get_tag(tag)
                    except models.Tag.DoesNotExist:
                        print "The tag " + str(tag) + " does not exist."
                        return
                    
                    tagged = tag in activity.tags.all()
                    
                    if tags_operator == "AND":
                        fits = fits and tagged
                        if not fits:
                            break
                    elif tags_operator == "OR":
                        fits = fits or tagged
                        if fits:
                            break
                        
                if fits:
                    final_list.append(activity)
        else:
            final_list = activities
        
        if days is not None:
            split_days = days.split(",")
            tmp_days = []
            for day in split_days:
                day.strip()
                try:
                    day = int(day)
                except:
                    raise TravelAppException("Day must be an integer (eg: 2 would be the second day)")
                tmp_days.append(day)
            split_days = tmp_days
            
            new_list = []
            
            for activity in final_list:
                time_intervals = activity.timeinterval_set.all()
                for time_interval in time_intervals:
                    if time_interval.day.order in split_days:
                        new_list.append(activity)
                        break

            final_list = new_list
            
        self.current_activities = final_list
        return final_list
        
    def _get_activities(self):
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to get activities. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to get activities. Please goto a trip.")

        return models.TripActivity.objects.filter(trip = self.current_trip)
     
        
    def plan(self, activity_id, day, time_interval=None):
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to get an activity. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to plan an activity. Please goto a trip.")

        start_time = None
        end_time = None
        if time_interval is not None:
            start = time_interval[0]
            end = time_interval[1]
            
            while len(start) < 4:
                start = "0" + start
            while len(end) < 4:
                end = "0" + end
                
            try:
                start_time = datetime.time(int(start[0:2]), int(start[2:]))
                end_time = datetime.time(int(end[0:2]), int(end[2:]))
            except:
                raise TravelAppException("Either the start or end time was improperly formatted. For best result, format like hhmm")

        activity = self.get_activity(activity_id)
        day = self.get_day(day)
        
        db_time_interval = models.TimeInterval(activity = activity, day = day, start_time=start_time, end_time=end_time)
        db_time_interval.save()

        print_str = "successfully planned " + str(activity) + " for day " + str(day)
        if start_time is not None and end_time is not None:
            print_str += " from " + str(start_time) + " to " + str(end_time) 
        print print_str 
            
class TravelAppCmdLine(cmd.Cmd):
    tag_regex = re.compile("^-[a-zA-Z]$")
    travel_app = TravelApp()
    
    def find_next_tag(self, line_split):
        for i in range(len(line_split)):
            result = self.tag_regex.match(line_split[i])
            if result:
                return i
            
        return None
    
    def print_businesses(self, businesses):
        for i in range(len(businesses)):
            print "[" + str(i) + "] " + self.travel_app.pretty_string_business(businesses[i])
            
    def print_activities(self, activities):
        if activities is None:
            print "No activities"
        else:      
            print "(priority) [id] activity name (tags)"
            print "-------------------"
            for activity in activities:
                print activity
      
    def print_day(self, day):
        print_str = "[" + str(day.order) + "]"
        if day.date is not None:
            print_str += " " + str(day.date)
        print print_str
        
        all_days = day.timeinterval_set.filter(start_time=None)
        part_days = day.timeinterval_set.exclude(start_time=None)
        
        if len(all_days) > 0:
            print "  [[ all day events ]]"
            for all_day in all_days:
                print "    " + str(all_day.activity)
                
        if len(part_days) > 0:
            print "  [[ partial day events ]]"
            for part_day in part_days:
                print ("    " + str(part_day.activity) + " (" + str(part_day.start_time) + "-" +
                       str(part_day.end_time) + ") ")
      
    def list_tags(self, line):
        try:
            tags = self.travel_app.get_tags()
            print "[id] tag name"
            print "---------------"
            for tag in tags:
                print "[" + str(tag.id) + "] " + tag.name
        except TravelAppException as e:
            print str(e)
        
    def list_trips(self, line):
        try:
            trips = self.travel_app.get_trips()
            print "[id] trip name"
            print "---------------"
            for trip in trips:
                print "[" + str(trip.id) + "] " + trip.name
        except TravelAppException as e:
            print str(e)
            
    def list_search(self, line):
        businesses = self.travel_app.current_search
        if businesses:
            self.print_businesses(businesses)
    
    def list_global_activities(self, line):
        try:
            global_activities = self.travel_app.get_global_activities()
            for activity in global_activities:
                print activity
        except TravelAppException as e:
            print str(e)
    
    def list_activities(self, line):
        line_split = line.split(" ")
        days = None
        tags = None
        tag_operator = None
        activities = None
        
        if len(line_split) == 1:
            if len(line_split[0]) == 0:
                line_split = []
            elif line_split[0] == "-c":
                activities = self.travel_app.current_activities
                line_split = line_split[1:]
        
        if activities is None:
            while(len(line_split) > 0):
                index = self.find_next_tag(line_split[1:])
                if index:
                    index += 1
                else:
                    index = len(line_split)
                if line_split[0] == "-t":
                    tag_operator = "AND"
                    if line_split[1] == "AND" or line_split[1] == "OR":
                        tag_operator = line_split[1]
                        tags = " ".join(line_split[2:index])
                    else:
                        tags = " ".join(line_split[1:index])
                elif line_split[0] == "-d":
                    days = " ".join(line_split[1:index])
                    
                else:
                    print "Error: that command does not exist. Type 'help' for a listing of commands."
                    return
                
                line_split=line_split[index:]
                
            try:
                activities = self.travel_app.get_activities(tags, tag_operator, days)
            except TravelAppException as e:
                print str(e)
                return
            
        self.print_activities(activities)
        """
        try:
            activities = self.travel_app.get_activities()
            self.print_activities(activities)
        except TravelAppException as e:
            print str(e)
        """
            
    def list_days(self, line):
        try:
            days = self.travel_app.get_days()
            print "[day number] date"
            print "-----------------"
            for day in days:
                self.print_day(day)
        except TravelAppException as e:
            print str(e)
            
    def delete_tag(self, line):
        try:
            self.travel_app.delete_tag(line)
        except TravelAppException as e:
            print str(e)
            
    def delete_trip(self, line):
        try:
            self.travel_app.delete_trip(line)
        except TravelAppException as e:
            print str(e)
        
    def delete_activity(self, line):
        try:
            self.travel_app.delete_activity(line)
        except TravelAppException as e:
            print str(e)
        
    def create_user(self, line):
        error_string = "Usage error: create user -u <username> -n <name>."

        line_split = line.split(" ")
        if len(line_split) < 4:
            print error_string
        else:
            username = ""
            name = ""
            while(len(line_split) > 0):
                index = self.find_next_tag(line_split[1:])
                if index:
                    index += 1
                if len(line_split) > 1:
                    if line_split[0] == '-u':
                        if index and index > 2:
                            print "Usage error: a username cannot contain spaces."
                            return
                        username = line_split[1]
                        line_split = line_split[2:]
                    elif line_split[0] == '-n':
                        if index and index == 1:
                            # don't have a name entry
                            print error_string
                            return
    
                        if index:
                            name = " ".join(line_split[1:index])
                            line_split = line_split[index:]
                        else:                    
                            name = " ".join(line_split[1:])
                            line_split = []
                    else:
                        print error_string
                        return
                else:
                    print error_string
                    return
                
            if len(username) > 0 and len(name) > 0:
                try:
                    self.travel_app.create_user(username, name)
                except TravelAppException as e:
                    print str(e)
            else:
                print error_string
    
    def create_tag(self, line):
        try:
            self.travel_app.create_tag(line)
        except TravelAppException as e:
            print str(e)
            
    def create_trip(self, line):
        error_string = "Usage error: create trip <name> [-d <start_date (yyyy-mm-dd)> -l <length>]"
        line_split = line.split(" ")
        
        if len(line_split) < 1:
            print error_string
            return
        
        index = self.find_next_tag(line_split)
        if index == 0:
            print error_string
            return
        
        start_date = None
        length = None
        
        name = line_split[0]
        line_split = line_split[1:]
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index:
                index += 1
            else:
                index = len(line_split)
                
            if line_split[0] == "-d":
                start_date = line_split[1]
            if line_split[0] == "-l":
                length = line_split[1]
                
            line_split = line_split[index:]

        try:
            self.travel_app.create_trip(name=name, start_date=start_date, duration=length)
        except TravelAppException as e:
            print str(e)

    def create_activity(self, line):
        error_string = "Usage error: create activity <name>"
        line_split = line.split(" ")
        
        if len(line_split) < 1:
            print error_string
            return
        
        index = self.find_next_tag(line_split)
        if index == 0:
            print error_string
            return
        
        public = False
        country_code = None
        name = " ".join(line_split[0:index])
        line_split = line_split[index:]
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index:
                index += 1
            else:
                index = len(line_split)
                
            if line_split[0] == "-p":
                public = True
            elif line_split[0] == "-c":
                country_code = line_split[1]
            else:
                print error_string
                return
                
            line_split = line_split[index:]

        try:
            self.travel_app.create_activity(name=name, public=public, country_code=country_code)
        except TravelAppException as e:
            print str(e)

    def edit_trip(self, line):
        error_string = "Usage error: edit trip name [-n <new name> -d <start_date (yyyy-mm-dd)> -l <length>]"
        line_split = line.split(" ")
        
        if len(line_split) < 1:
            print error_string
            return
        
        index = self.find_next_tag(line_split)
        if index == 0:
            print error_string
            return
        
        start_date = None
        length = None
        new_name = None
        
        name = line_split[0]
        line_split = line_split[1:]
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index is not None:
                index += 1
            else:
                index = len(line_split)
                
            if line_split[0] == "-d":
                print "in date"
                start_date = line_split[1]
            if line_split[0] == "-l":
                print "in length"
                length = line_split[1]
            if line_split[0] == "-n":
                print "in name"
                new_name = line_split[1]
                
            print index
            print line_split
            line_split = line_split[index:]
            print line_split

        try:
            self.travel_app.edit_trip(name=name, start_date=start_date, duration=length, new_name=new_name)
        except TravelAppException as e:
            print str(e)
        
    def edit_activity(self, line):
        """
        error_string = "Usage error: edit activity id [-n <new name> -d <start_date (yyyy-mm-dd)> -l <length>]"
        line_split = line.split(" ")
        
        if len(line_split) < 1:
            print error_string
            return
        
        index = self.find_next_tag(line_split)
        if index == 0:
            print error_string
            return
        """
        print "not yet implemented"
    def edit_global_activity_location(self, activity_id, line):
        error_string = ("Usage error: edit global_activity <id> location "
                        "[-o <latitude_coordinate longitude_coordinate>]")
        line_split = line.split(" ")
        
        if len(line_split) < 1:
            print error_string
            return
        
        country_code = None
        state_code = None
        city = None
        display_address = None
        address = None
        neighborhoods = None
        postal_code = None
        coordinate = None
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index is not None:
                index += 1
            else:
                index = len(line_split)
            
            if line_split[0] == "-c":
                country_code = line_split[1]
            elif line_split[0] == "-s":
                state_code = line_split[1]
            elif line_split[0] == "-y":
                print "in city"
                city = " ".join(line_split[1:index])
            elif line_split[0] == "-d":
                display_address = " ".join(line_split[1:index])
            elif line_split[0] == "-a":
                address = " ".join(line_split[1:index])
            elif line_split[0] == "-n":
                neighborhoods = " ".join(line_split[1:index]).split(",")
                new_neighborhoods = []
                    
                for neighborhood in neighborhoods:
                    new_neighborhoods.append(neighborhood.strip())
                
                neighborhoods = new_neighborhoods
            elif line_split[0] == "-p":
                postal_code = " ".join(line_split[1:index])
            elif line_split[0] == "-o":
                coordinate = " ".join(line_split[1:index])
            else:
                print "bad command: " + line_split[0]
                print error_string
                
            line_split = line_split[index:]
            
        try:
            self.travel_app.edit_global_activity_location(activity_id,
                                                          country_code,
                                                          state_code,
                                                          city,
                                                          display_address,
                                                          address,
                                                          neighborhoods,
                                                          postal_code,
                                                          coordinate)
        except TravelAppException as e:
            print str(e)
        
    def edit_global_activity(self, line):
        error_string = ("Usage error: edit global_activity <id> "
                        "[location <location info>] "
                        "[categories <categories info>] "
                        "[-r <rating>] [-c <review count>] [-d <description>] "
                        "[-n <name>]")
        line_split = line.split(" ")
        
        if len(line_split) < 1:
            print error_string
            return
        
        index = self.find_next_tag(line_split)
        if index == 0:
            print error_string
            return
        
        activity_id = line_split[0]
        line_split = line_split[1:]
        
        if line_split[0] == "location":
            self.edit_global_activity_location(activity_id, " ".join(line_split[1:]))
            return
        if line_split[0] == "categories":
            self.edit_global_activity_categories(activity_id, line_split[1:])
            return
        
        rating = None
        review_count = None
        phone = None
        description = None
        name = None
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index is not None:
                index += 1
            else:
                index = len(line_split)
                
            if line_split[0] == "-r":  # rating
                rating = line_split[1]
            elif line_split[0] == "-c":  # review count
                review_count = line_split[1]
            elif line_split[0] == "-p":  # phone
                phone = " ".join(line_split[1:index])
            elif line_split[0] == "-d":  # description
                description = " ".join(line_split[1:index])
            elif line_split[0] == "-n": #name
                name = " ".join(line_split[1:index])
            else:
                print error_string
                
            line_split = line_split[index:]
            
        try:
            self.travel_app.edit_global_activity(activity_id, rating, review_count, phone, description, name)
        except TravelAppException as e:
            print str(e)

    
    def add_activity(self, line):
        index = -1
        try:
            index = int(line)
        except:
            print "The argument to add activity should be the index of the activity"
            return
        
        try:
            self.travel_app.add_activity(index)
        except TravelAppException as e:
            print str(e)

    def do_logout(self, line):
        if len(line) > 0:
            print "Usage error: logout takes no arguments"
            return
        try:
            self.travel_app.logout()
        except TravelAppException as e:
            print str(e)
    
    def do_login(self, line):
        line_split = line.split(" ")
        if len(line_split) > 1:
            print "Usage error: username cannot contain spaces"
            return
        try:
            self.travel_app.login(line)
        except TravelAppException as e:
            print str(e)
    
    def do_list(self, line):
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
        
        line = " ".join(line_split[1:])
        first_item = line_split[0]
        if first_item == "tags":
            self.list_tags(line)
        elif first_item == "trips":
            self.list_trips(line)
        elif first_item == "search":
            self.list_search(line)
        elif first_item == "activities":
            self.list_activities(line)
        elif first_item == "days":
            self.list_days(line)
        elif first_item == "global_activities":
            self.list_global_activities(line)
        else:
            print "Error: that command does not exist. Type 'help' for a listing of commands."
    
    def do_delete(self, line):    
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
        
        line = " ".join(line_split[1:])
        first_item = line_split[0]
        if first_item == "tag":
            self.delete_tag(line)
        elif first_item == "trip":
            self.delete_trip(line)
        elif first_item == "activity":
            self.delete_activity(line)
        else:
            print "Error: that command does not exist. Type 'help' for a listing of commands."
            
    def do_search(self, line):
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"

        category_filter = None
        location = None
        term = None
        limit = None
        offset = None
        sort = None
        radius_filter = None
        deals_filter = None
        cc = None
        lang = None
        bounds = None
        ll = None
        cll = None
        
        print line_split
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index:
                index += 1
            else:
                index = len(line_split)
            if line_split[0] == "-c":
                category_filter = " ".join(line_split[1:index])
            elif line_split[0] == "-l":
                location = " ".join(line_split[1:index])
                print location
            elif line_split[0] == "-t":
                term = " ".join(line_split[1:index])
                print term
            elif line_split[0] == "-i":
                limit = " ".join(line_split[1:index])
            elif line_split[0] == "-o":
                offset = " ".join(line_split[1:index])
            elif line_split[0] == "-s":
                sort = " ".join(line_split[1:index])
            elif line_split[0] == "-r":
                radius_filter = " ".join(line_split[1:index])
            elif line_split[0] == "-d":
                deals_filter = " ".join(line_split[1:index])
            elif line_split[0] == "-C":
                cc = " ".join(line_split[1:index])
            elif line_split[0] == "-a":
                lang = " ".join(line_split[1:index])
            elif line_split[0] == "-b":
                bounds = " ".join(line_split[1:index])
            elif line_split[0] == "-L":
                ll = " ".join(line_split[1:index])
            elif line_split[0] == "-x":
                cll = " ".join(line_split[1:index])

            line_split=line_split[index:]
            
        try:
            businesses = self.travel_app.search(category_filter, location, term, limit, offset, sort, radius_filter, deals_filter, cc, lang, bounds, ll, cll)
        except TravelAppException as e:
            print str(e)
            return
            
        self.print_businesses(businesses)
                    
    def do_create(self, line):
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
        
        line = " ".join(line_split[1:])
        first_item = line_split[0]
        if first_item == "user":
            self.create_user(line)
        elif first_item == "tag":
            self.create_tag(line)
        elif first_item == "trip":
            self.create_trip(line)
        elif first_item == "activity":
            self.create_activity(line)
        else:
            print "Error: that command does not exist. Type 'help' for a listing of commands."

    def do_edit(self, line):
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
        
        line = " ".join(line_split[1:])
        first_item = line_split[0]
        if first_item == "trip":
            self.edit_trip(line)
        if first_item == "activity":
            self.edit_activity(line)
        if first_item == "global_activity":
            self.edit_global_activity(line)
        else:
            print "Error: that command does not exist. Type 'help' for a listing of commands."
            
    def do_goto(self, line):
        if len(line) > 0:
            try:
                self.travel_app.goto(line)
            except TravelAppException as e:
                print str(e)
        else:
            print "You must enter a destination."
        
    def do_leave(self, line):
        try:
            self.travel_app.leave()
        except TravelAppException as e:
            print str(e)
            
    def do_status(self, line):
        current_user = self.travel_app.current_user
        current_trip = self.travel_app.current_trip
        
        if current_user:
            print "You are currently logged in as " + current_user.username
            if current_trip:
                print "You are currently exploring " + str(current_trip)
        else:
            print "You are not logged in"
    
    def do_add(self, line):
        self.add_activity(line)
        """ only have one command for now, so going straight there 
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
        
        line = " ".join(line_split[1:])
        first_item = line_split[0]
        if first_item == "activity":
            self.add_activity(line)
        else:
            print "Error: that command does not exist. Type 'help' for a listing of commands."
        """
        
    def do_tag(self, line):
        """ -f: force """
        error_string = "Usage error: tag -a <activity id> -t <tagname or id> [-f]"
        
        line_split = line.split(" ")
        if len(line_split) < 4:
            print error_string
        else:
            activity_id = -1
            tagname_or_id = ""
            force = False
            
            while(len(line_split) > 0):
                index = self.find_next_tag(line_split[1:])
                if index:
                    index += 1
                if len(line_split) > 1:
                    if line_split[0] == '-a':
                        if index is not None and index != 2:
                            print "Usage error: an activity id must exist and cannot contain spaces."
                            return
                        try:
                            activity_id = int(line_split[1])
                        except:
                            print "Usage error: an activity id must be an integer"
                            return
                    elif line_split[0] == '-t':
                        if index and index == 1:
                            # don't have a tag entry
                            print "don't have tag entry"
                            print error_string
                            return
    
                        if index is not None:
                            tagname_or_id = " ".join(line_split[1:index])
                        else:                    
                            tagname_or_id = " ".join(line_split[1:])
                    elif line_split[0] == '-f':
                        if index and index != 1:
                            return
                        force = True
                    else:
                        print error_string
                        return
                    
                    if index:
                        line_split = line_split[index:]
                    else:
                        line_split = []
                
            if activity_id >= 0 and len(tagname_or_id) > 0:
                try:
                    self.travel_app.tag_activity(activity_id, tagname_or_id, force)
                except TravelAppException as e:
                    print str(e) 
            else:
                print error_string
                return
       
    def do_untag(self, line):
        error_string = "Usage error: untag -a <activity id> -t <tagname or id>"
        
        line_split = line.split(" ")
        if len(line_split) < 4:
            print error_string
        else:
            activity_id = -1
            tagname_or_id = ""
            
            while(len(line_split) > 0):
                index = self.find_next_tag(line_split[1:])
                if index:
                    index += 1
                if len(line_split) > 1:
                    if line_split[0] == '-a':
                        if index is not None and index != 2:
                            print "Usage error: an activity id must exist and cannot contain spaces."
                            return
                        try:
                            activity_id = int(line_split[1])
                        except:
                            print "Usage error: an activity id must be an integer"
                            return
                    elif line_split[0] == '-t':
                        if index and index == 1:
                            # don't have a tag entry
                            print error_string
                            return
    
                        if index:
                            tagname_or_id = " ".join(line_split[1:index])
                        else:                    
                            tagname_or_id = " ".join(line_split[1:])
                    else:
                        print error_string
                        return
                    
                    if index:
                        line_split = line_split[index:]
                    else:
                        line_split = []
                
            if activity_id >= 0 and len(tagname_or_id) > 0:
                try:
                    self.travel_app.untag_activity(activity_id, tagname_or_id)
                except TravelAppException as e:
                    print str(e) 
            else:
                print error_string
                
    def do_order(self, line):
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
            return
        
        activity_ids = []
        line_split = line.split(",")
        for activity_id in line_split:
            activity_id = activity_id.strip()
            try:
                activity_id = int(activity_id)
            except:
                print "The list of ids must all be integers"
                return
            
            activity_ids.append(activity_id)
            
        try:
            activities = self.travel_app.order(activity_ids)
            print "ordered activities:"
            self.print_activities(activities)
        except TravelAppException as e:
            print str(e)
            
    def do_plan(self, line):
        error_string = "Usage error: plan -a <activity id> -d <day> [-t <time interval ('1600 2000' for 4pm to 8pm)>]"
        
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
            
        time_interval_start = None
        time_interval_end = None
        
        while(len(line_split) > 0):
            index = self.find_next_tag(line_split[1:])
            if index:
                index += 1
            else:
                index = len(line_split)
                
            if line_split[0] == "-a":
                if index is not None and index != 2:
                    print "Usage error: an activity id must exist and cannot contain spaces."
                    print error_string
                    return
                try:
                    activity_id = int(line_split[1])
                except:
                    print "Usage error: an activity id must be an integer"
                    return
            elif line_split[0] == "-d":
                if index is not None and index != 2:
                    print "Usage error: a day must exist and cannot contain spaces."
                    print error_string
                    return
                day = line_split[1]
            elif line_split[0] == "-t":
                if index is not None and index != 3:
                    print error_string
                    return
                time_interval_start = line_split[1]
                time_interval_end = line_split[2]
            else:
                print "Error: that command does not exist. Type 'help' for a listing of commands."
                return

            if index:
                line_split = line_split[index:]
            else:
                line_split = []
                
        if activity_id is not None and day is not None:
            time_interval = None
            if time_interval_start is not None and time_interval_end is not None:
                time_interval = (time_interval_start, time_interval_end)
            try:
                self.travel_app.plan(activity_id, day, time_interval)
            except TravelAppException as e:
                print str(e)
        else:
            print error_string
            return
   
    def do_greet(self, line):
        print "hello"
        
    def do_EOF(self, line):
        """ documentation """
        return True

    def do_test1(self, line):
        activities = models.Activity.objects.all()
        activity = activities[6] 
        print activity.yelp_id
        activity.yelp_id = "something"
        print activity.yelp_id
        #activity.save()

if  __name__ =='__main__':TravelAppCmdLine().cmdloop()
