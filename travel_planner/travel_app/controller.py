import models
import cmd
import django.db
import re
import requester

class TravelAppException(Exception):
    """ An exception for a travel app """

class TravelApp:
    current_user = None
    current_trip = None
    current_businesses = None
    
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
        result = requester.get_yelp_request(category_filter, location, term, limit, offset, sort, radius_filter, deals_filter, cc, lang, bounds, ll, cll)
        self.current_businesses = result
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
        self.current_businesses = None
        
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
         
    def create_trip(self, name):
        self.create_generic(name, models.Trip)  
        
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
        print "You have successfully saved \"" + str(item) + "\""

    def goto(self, trip):
        trip = self.get_trip(trip)
        self.current_trip = trip
        
    def leave(self):
        self.current_trip = None
          
    def get_generic(self, identifier, model_class):
        if not self.current_user:
            raise TravelAppException("You must be logged in to add a tag. Please login.")
        
        item = None
        if self.letter_regex.match(identifier):
            item = model_class.objects.get(name=identifier, user=self.current_user)
        else:
            item = model_class.objects.get(id=int(identifier))
            
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

        return models.TripActivity.objects.get(id = identifier)
   
    def get_generics(self, model_class):
        if not self.current_user:
            raise TravelAppException("You must be logged in to get objects. Please login.")

        return model_class.objects.filter(user = self.current_user)
        
    def get_tags(self):
        return self.get_generics(models.Tag)

    def get_trips(self):
        return self.get_generics(models.Trip)

    def get_activities(self):
        if not self.current_user:
            raise TravelAppException("You must be logged in and in a trip to get activities. Please login.")
        if not self.current_trip:
            raise TravelAppException("You must be in a trip to get activities. Please goto a trip.")

        return models.TripActivity.objects.filter(trip = self.current_trip)
    
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
        activity = self.current_businesses[index]
        db_yelp_activity = models.YelpActivity.get_or_create(activity)
        db_activity = models.Activity.get_or_create(yelp_activity = db_yelp_activity)
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
            
    def filter(self, tags = None, tags_operator = "AND"):
        activities = self.get_activities()
        
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
                    
            
        return final_list
            
        
            
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
            print "[id] activity name (tags)"
            print "-------------------"
            for activity in activities:
                print_str ="[" + str(activity.id) + "] " + activity.name
                
                if len(activity.tags.all()) > 0:
                    print_str += " ("
                    for tag in activity.tags.all():
                        print_str += tag.name + ", "
                    print_str = print_str[:-2]
                    print_str += ")"
                
                print print_str 
      
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
        businesses = self.travel_app.current_businesses
        if businesses:
            self.list_businesses(businesses)
            
    def list_activities(self, line):
        try:
            activities = self.travel_app.get_activities()
            self.print_activities(activities)
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
        try:
            self.travel_app.create_trip(line)
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
            
        businesses = self.travel_app.search(category_filter, location, term, limit, offset, sort, radius_filter, deals_filter, cc, lang, bounds, ll, cll)
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
                print "You are currently exploring " + current_trip.name
        else:
            print "You are not logged in"
    
    def do_add(self, line):
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
        
        line = " ".join(line_split[1:])
        first_item = line_split[0]
        if first_item == "activity":
            self.add_activity(line)
        else:
            print "Error: that command does not exist. Type 'help' for a listing of commands."
        
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
        
    def do_filter(self, line):
        # TODO: consider adding -g for geographic filtering with a radius
        # TODO: consider adding -d for day filtering
        line_split = line.split(" ")
        if len(line_split) < 1 or len(line_split[0]) == 0:
            print "Error: must include at least one argument"
            
        tags = None
        
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
            else:
                print "Error: that command does not exist. Type 'help' for a listing of commands."
                return
            
            line_split=line_split[index:]
            
        activities = None
        try:
            activities = self.travel_app.filter(tags, tag_operator)
            self.print_activities(activities)
        except TravelAppException as e:
            print str(e)
            return
        
    def do_greet(self, line):
        print "hello"
        
    def do_EOF(self, line):
        """ documentation """
        return True



if  __name__ =='__main__':TravelAppCmdLine().cmdloop()
