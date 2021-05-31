import discord, json, time, os, asyncio, random
from discord.ext import commands,tasks, menus

"""

CLASSES

"""

class Room:
    
    def __init__(self, room_chat_channel, room_items_channel, room_role):
        self.room_chat_channel = room_chat_channel
        self.name = room_chat_channel.name
        self.room_items_channel = room_items_channel
        self.room_role = room_role

        self.items_embed = None
        self.items_embed_message = None
    
    async def add_body_to_room(self, Bodytype, rooms_dict):
        items_list_in_room = rooms_dict[self.name]["Items"]
        rooms_dict[self.name]["Bodies"].append(Bodytype)
        bodies_in_room = rooms_dict[self.name]["Bodies"]
        desc = "\n".join([item_type.name for item_type in items_list_in_room] + [body.name for body in bodies_in_room])
        self.items_embed = discord.Embed(
            title = self.room_role.name,
            description = desc)
        await self.items_embed_message.edit(embed = self.items_embed)
        return rooms_dict
    
    async def remove_body_from_room(self, Bodytype, rooms_dict):
        items_list_in_room = rooms_dict[self.name]["Items"]
        bodies_in_room = rooms_dict[self.name]["Bodies"]
        if Bodytype in bodies_in_room:
            rooms_dict[self.name]["Bodies"].remove(Bodytype)
            bodies_in_room = rooms_dict[self.name]["Bodies"]
            if not (any(items_list_in_room) and any(bodies_in_room)):
                self.items_embed = discord.Embed(
                    title = self.room_role.name,
                    description = "No items")
                await self.items_embed_message.edit(embed = self.items_embed)
            else:
                desc = "\n".join([item_type.name for item_type in items_list_in_room] + [body.name for body in bodies_in_room])
                self.items_embed = discord.Embed(
                    title = self.room_role.name,
                    description = desc)
                await self.items_embed_message.edit(embed = self.items_embed)
            return rooms_dict
        return False

    async def add_item_to_room(self, item_type, rooms_dict):
        rooms_dict[self.name]["Items"].append(item_type)
        items_list_in_room = rooms_dict[self.name]["Items"]
        bodies_in_room = rooms_dict[self.name]["Bodies"]
        desc = "\n".join([item_type.name for item_type in items_list_in_room] + [body.name for body in bodies_in_room])
        self.items_embed = discord.Embed(
            title = self.room_role.name,
            description = desc)
        await self.items_embed_message.edit(embed = self.items_embed)
        return rooms_dict
    
    async def remove_item_from_room(self, item_type, rooms_dict):
        items_list_in_room = rooms_dict[self.name]["Items"]
        bodies_in_room = rooms_dict[self.name]["Bodies"]
        if item_type in items_list_in_room:
            rooms_dict[self.name]["Items"].remove(item_type)
            items_list_in_room = rooms_dict[self.name]["Items"]
            
            if not (any(items_list_in_room) or any(bodies_in_room)):
                self.items_embed = discord.Embed(
                    title = self.room_role.name,
                    description = "No items")
                await self.items_embed_message.edit(embed = self.items_embed)
            else:
                desc = "\n".join([item_type.name for item_type in items_list_in_room] + [body.name for body in bodies_in_room])
                self.items_embed = discord.Embed(
                    title = self.room_role.name,
                    description = desc)
                await self.items_embed_message.edit(embed = self.items_embed)
            return rooms_dict
        return False
    
    async def initialize_items_message(self):
        desc = "No items"
        self.items_embed = discord.Embed(
            title = self.room_role.name,
            description = desc)
        self.items_embed_message = await self.room_items_channel.send(embed = self.items_embed)
        return True
    
    @staticmethod
    async def create(room_chat_channel, room_items_channel, room_role):
        room_type = Room(room_chat_channel, room_items_channel, room_role)
        await room_type.initialize_items_message()
        return room_type



class Player:
    
    """A Player class. Stores relevant information and 
    functions relating to all 9 (or less) players in Dispatched."""

    def __init__(self, member_type):
        self.member_type = member_type
        self.name = self.member_type.name
        self.nickname = self.member_type.display_name

        #Room
        self.private_channel = None
        self.Room = None
        self.embed_color = None

        #character_type
        self.character_type = None
        self.character_name = None
        self.character_embed = None

        #Carrying
        self.items = []
        self.body = None
        self.is_carrying = None #player object or body object?

        #relevant for moves message
        self.default_turn_embed = True
        self.idle = False
        self.entity_type = None
        self.is_entity = False
        self.can_play = False #Resets at the start of every round

        self.is_dead = False
        self.has_escaped = False
        self.is_infected = False

        #tied up or injured can be carried and cannot move
        self.carried_by = None
        self.is_injured = False
        self.is_tied = None #contains the rope object if the person is tied?
    
    @property
    def weight(self):
        return len(self.items) + (self.is_carrying != None)

    def is_max_weight(self):
        if not (self.weight < 2):
            return True
        return False


    @property
    def can_be_carried(self):
        return ((self.carried_by == None) and (self.is_injured or self.is_tied))

    def set_can_play_false(self):
        self.can_play = False
    
    def set_can_play_true(self):
        self.can_play = True

    async def kill(self, Dead_role, rooms_dict, with_messages = True): 
        """A player dies. Their items drop, an unpickable Item is created
        in the player's name, the player gains the role "Dead", loses their
        room's role, and so on. May behave differently if the player is 
        the entity/if the kill uses a flame thrower. Shows the Corpse in
        the room."""
        current_Room = rooms_dict[self.Room.room_chat_channel.name]["Room"]
        rooms_dict[self.Room.name]["Players"].remove(self)
        for item in self.items:
            rooms_dict = await current_Room.add_item_to_room(item, rooms_dict)
        self.items = []
        if self.body != None:
            rooms_dict = await current_Room.add_body_to_room(self.body, rooms_dict)
            rooms_dict = self.body.is_pickable = True
            self.body = None
        self.is_dead = True
        await self.member_type.remove_roles(self.Room.room_role)
        await self.member_type.add_roles(Dead_role)
        Body_type = Body(self.character_name)
        rooms_dict = await current_Room.add_body_to_room(Body_type, rooms_dict)
        if with_messages:
            await self.private_channel.send(f"You died, {self.character_name}! :(")
            await current_Room.room_chat_channel.send(f"*{self.character_name} dies.*")
        return rooms_dict
    
    async def pick_body(self,Body_type):
        self.body = Body_type
        self.body.is_pickable = False
        return True
    
    async def drop_body(self):
        self.body = None
        self.body.is_pickable = True
        return True

    async def add_private_channel_to_player(self, ctx, private_channel):
        """Adds a role for the right private channel for a player. 
        Saves that channel's discord.channel type for further use."""
        self.private_channel = private_channel
        for server_role in ctx.guild.roles:
            #print(strip(server_role.name), private_channel.name)
            if strip(server_role.name) == private_channel.name:
                role = server_role
        await self.member_type.add_roles(role)
        return True

    async def move_room(self, new_Room, rooms_dict, with_messages = True):
        rooms_dict[self.Room.name]["Players"].remove(self)
        rooms_dict[new_Room.name]["Players"].append(self)
        current_Room = self.Room
        await self.member_type.remove_roles(self.room_role)
        if with_messages:     
            await current_Room.room_chat_channel.send(f"*{self.character_name} leaves toward {new_Room.name.replace('-', ' ')}*")
            await new_Room.room_chat_channel.send(f"*{self.character_name} enters from {current_Room.name.replace('-', ' ')}*")
        self.Room = new_Room
        self.room_role = self.Room.room_role
        self.room_chat_channel = self.Room.room_chat_channel
        await self.member_type.add_roles(self.room_role)

        #Deal with bodies and players being carried
        if type(self.is_carrying) == Player:
            await current_Room.room_chat_channel.send(f"*... and drags {self.is_carrying.character_name}({('TIED UP' if self.is_carrying.is_tied else 'INJURED')}) with them.*")
            rooms_dict = self.is_carrying.move_room(new_Room, rooms_dict, with_messages= False)
            await new_Room.room_chat_channel.send(f"*... and drags {self.is_carrying.character_name}({('TIED UP' if self.is_carrying.is_tied else 'INJURED')}) with them.*")
        
        elif type(self.is_carrying) == Body:
            body_type = self.is_carrying
            await current_Room.remove_body_from_room(body_type)
            await current_Room.room_chat_channel.send(f"*... and drags {body_type.character_name}'s body with them.*")
            await new_Room.add_body_to_room(self.is_carrying)
            await new_Room.room_chat_channel.send(f"*... and drags {body_type.character_name}'s bdoy with them.*")
        
        await self.private_channel.send(f"**You successfully moved to {new_Room.name.replace('-', ' ')}.**")
        
        return rooms_dict
    
    async def place_player_in_room(self, Room):
        self.Room = Room
        self.room_role = self.Room.room_role
        self.room_chat_channel = self.Room.room_chat_channel
        await self.member_type.add_roles(self.room_role)

    def recreate_nickname(self):
        """Recreates a nickname from the Player's character's name
        as well as all the names of the items the player is holding"""
        self.nickname = self.character_name
        if self.items != []:
            for item in self.items:
                self.nickname += f'({item.name})'
        return self.nickname

    async def add_item_to_inv(self, item_type, rooms_dict):
        """Takes in an item type and adds that item to a
        Player's list of items. It also edits that player's
        nickname to include that item's name."""
        self.items.append(item_type)
        
        #infect the player, and uninfect the item, if the item is infected.
        if item_type.is_infected and not self.is_entity:
            self.is_infected = True
            item_type.is_infected = False
            
        self.recreate_nickname()
        await self.member_type.edit(nick = self.nickname)

        await self.private_channel.send(f"**You successfully picked {aORan(item_type.name)}.**")
        await self.Room.room_chat_channel.send(f"*{self.character_name} picks {aORan(item_type.name)}.*")
        
        await self.Room.remove_item_from_room(item_type, rooms_dict)

        return True
    
    async def drop_item_from_inv(self, item_type, rooms_dict):
        """Takes in an item type and removes it from
        the Player and removes it from the nickname, if that player
        is holding said weapon."""
        if item_type in self.items:
            self.items.remove(item_type)
            self.nickname = self.recreate_nickname()
            await self.member_type.edit(nick = self.nickname)

            await self.private_channel.send(f"**You successfully dropped {aORan(item_type.name)}**.")
            await self.Room.room_chat_channel.send(f"*{self.character_name} drops {aORan(item_type.name)}.*")
        
            await self.Room.add_item_to_room(item_type, rooms_dict)

            return True
        else:
            return False

    async def give_entity_to_player(self, entity_embed):
        self.is_entity = True
        self.entity_type = Entity(self)
        
        await self.private_channel.send(embed = entity_embed.set_footer(
            text = "Do .info Entity for more information about the abilities."))
        
        return True
    
    async def add_character_to_player(self, character_type):
        self.character_type = character_type
        self.character_name = character_type.name
        self.character_embed = character_type.embed
        
        #change nickname
        self.nickname = self.recreate_nickname()
        await self.member_type.edit(nick = self.nickname)
        
        return True

    def change_embed_color(self):
        if self.embed_color == None:
            self.embed_color = create_random_color()
            return self.embed_color
        self.embed_color = create_random_color(self.embed_color.to_rgb())
        return self.embed_color
        
    async def send_map_embed_to_private_channel(self):
        DispatchedInfo = await openDispatchedInfojson()
        map_url = DispatchedInfo["Information"]["Images"]["map"]
        map_embed = discord.Embed(title = "Outpost", color = self.embed_color).set_image(url = map_url)
        await self.private_channel.send(embed = map_embed)

    @staticmethod
    async def create(ctx, member_type, private_channel, Room, character_type):
        player_type = Player(member_type)
        await player_type.add_private_channel_to_player(ctx, private_channel)
        await player_type.place_player_in_room(Room)
        player_type.change_embed_color()
        await asyncio.sleep(0.1)
        #map
        await player_type.send_map_embed_to_private_channel()
        await asyncio.sleep(0.1)

        #init
        await player_type.add_character_to_player(character_type)
        player_type.character_embed.color = player_type.change_embed_color()

        initializationembed = player_type.character_embed.set_footer(
            text = "Please change your profile picture to the one shown above.\nDo .info for more information about Dispatched.\nDo .lessinfo to remove the room information from the turn messages.") 
        
        player_type.charembedmsg = await player_type.private_channel.send(embed = initializationembed)
        
        return player_type

    """
    TO ADD :
    When you add or remove an item and there's many items
    of the same name in the room or whatever, it asks you
    if you want to pick (or drop) the item with the most Fuel in it. (y,n)
    CanPlay function. If true, the player can make moves, otherwise they cant
    """



class Character:
    
    def __init__(self, name):
        self.name = name
    
    async def findembed(self, DispatchedInfo):
        title = self.name
        if self.name == "Entity":
            self.url = DispatchedInfo[self.name]["image_url"]
            desc = "\n".join(DispatchedInfo[self.name]["Abilities"])
            self.embed = discord.Embed(title = title, description = desc).set_image(url = self.url)
            return
        self.url = DispatchedInfo["Characters"][self.name]["image_url"]
        #Creates a list (separated by \n) of the character's abilities
        desc = "\n".join(DispatchedInfo["Characters"][self.name]["Abilities"])
        self.embed = discord.Embed(title = title, description = desc).set_image(url = self.url)
        return

    @staticmethod
    async def create(name, DispatchedInfo):
        character_type = Character(name)
        await character_type.findembed(DispatchedInfo)
        return character_type




class Item:
    
    def __init__(self, name):
        self.name = name
        self._contains = 0
        #Create a way to break items
        self.isBroken = False
        self.pickable = True
        self.isFillable = False
        self.washed = True
        self.is_infected = False
        #create a repair engineP thing
        self.isRepaired = False
    
    @property
    def contains(self):
        """Lets us use object.contains outside of the class as a getter"""
        return self._contains
    
    @contains.setter
    def contains(self, newvalue):
        """Setter method for .contains. Use with object.contains = newvalue.
        Sets an Item to the new value of contains, and turns 0 Fuel
        to EFuel and 1EFuel to Fuel"""
        self._contains = newvalue
        if self.name == "Fuel":
            if newvalue == 0:
                self.name = "EFuel"
                self.isFillable = True
        elif self.name == "EFuel":
            if newvalue == 1:
                self.name = "Fuel"
                self.isFillable = False
        if self.name == "FlameT":
            if newvalue == 2:
                self.isFillable = False
            if newvalue < 2:
                self.isFillable = True
        if newvalue == self.contains:
            return True
        return False
    
    def contains_initialization(self):
        """Initialization of the Item object. Gives Fuel 
        1 fuel and Fuel Barrel 2 fuels. None to every other item."""
        itemname = self.name
        if itemname == "Fuel":
            self.contains = 1
            return self.contains
        if itemname == "Fuel Barrel":
            self.contains = 2
            return self.contains
        else:
            return self._contains

    def breakitem(self):
        self.isBroken = True
        self.name += "(Broken)"
        self.pickable = False
        return self.isBroken
    
    def repair(self):
        if self.name == "EngineP" and not self.isRepaired:
            self.isRepaired = True
            return self.isRepaired
        return False

    @staticmethod
    def create(name, pickable = False):
        item_type = Item(name)
        item_type.contains_initialization()
        item_type.pickable = pickable
        if item_type.name == "FlameT":
            item_type.isFillable = True
        if item_type.name == "Test":
            item_type.washed = True
        return item_type





class Body:
    def __init__(self, character_name):
        self.character_name = character_name
        self.name = f"{character_name}'s body"
        self.is_pickable = True
        self.isBreached = False




class Entity:
    def __init__(self, player_type):
        self.isTransformed = False
        self.hasBreachedItem = False
        self.hasBreachedBody = False
        self.previousIdentities = []
        self.Abilitiesleft = 3
        self.hasHiddenPower = False
        self.FalseMortality = False
        

        
class MyMenu(menus.Menu):
    async def send_initial_message(self, ctx, channel):
        return await channel.send(f'Hello {ctx.author}')

    @menus.button('\N{THUMBS UP SIGN}')
    async def on_thumbs_up(self, payload):
        await self.message.edit(content=f'Thanks {self.ctx.author}!')

    @menus.button('\N{THUMBS DOWN SIGN}')
    async def on_thumbs_down(self, payload):
        await self.message.edit(content=f"That's not nice {self.ctx.author}...")

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f')
    async def on_stop(self, payload):
        self.stop()


class Confirm(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


def aORan(word):
    lower_case_word = ("".join(word)).lower()
    if lower_case_word[0] in ['a', 'e', 'i', 'o', 'u']:
        return f'an {word}'
    return f'a {word}'

def strip(string):
    string = string.lower()
    resultlst = list(string)
    for i in range(len(resultlst)):
        if resultlst[i] == " ":
            resultlst[i] = "-"
    result = "".join(resultlst)
    return result

async def openDispatchedInfojson():
    with open('DispatchedInfo.json', "r") as f:
        DispatchedInfo = json.load(f)
    return DispatchedInfo

def create_random_color(RGB = None):
    if RGB:
        return discord.Color.from_rgb(add_or_remove_15_to_rgb_value(RGB[0]), add_or_remove_15_to_rgb_value(RGB[1]), add_or_remove_15_to_rgb_value(RGB[2]))
    #random
    RGB = [int(180*random.random()) for i in range(3)]
    lstRGB = [i for i in RGB]
    return discord.Color.from_rgb(lstRGB[0], lstRGB[1], lstRGB[2])

def add_or_remove_15_to_rgb_value(number):
    number += (15 if random.random() > 0.5 else -15)
    if number < 1:
        number = 5
    elif number > 180:
        number = 175
    return number

async def ask_yes_no(ctx, question):
    confirm = await Confirm(question).prompt(ctx)
    return confirm
