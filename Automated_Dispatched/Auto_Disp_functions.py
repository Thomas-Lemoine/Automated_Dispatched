import discord, json, time, os, asyncio, random
from discord.ext import commands,tasks
from class_objects import Room, Character, Item, Player, Body, Entity

ADMINROLENAME = "Host"

"""FUNCTIONS"""

async def openDispatchedInfojson():
    with open('DispatchedInfo.json', "r") as f:
        DispatchedInfo = json.load(f)
    return DispatchedInfo


async def replace_channel_w_clone_and_delete(channel_to_replace):
    new_channel = await channel_to_replace.clone()
    await channel_to_replace.delete()
    return new_channel


def strip(string_to_strip):

    """This function transforms a room_role name to a room_chat name.
    Example : Outside Heli Upper -> outside-heli-upper"""

    string_to_strip = string_to_strip.lower()
    characters_list = list(string_to_strip)
    for i in range(len(characters_list)):
        if characters_list[i] == " ":
            characters_list[i] = "-"
    stripped_string = "".join(characters_list)
    return stripped_string


def scrambled(original_list):
    """
    This function returns the list, but scrambled.
    It doesn't modify the original list.
    """
    scrambled_list = original_list[:]
    random.shuffle(scrambled_list)
    return scrambled_list


def get_allowed_rooms_dict():
    Rooms = {
        "shed" : ["outside-shed"],
        "outside-shed" : ["shed", "garage", "outside-heli-upper"],
        "outside-heli-upper" : ["helicopter", "outside-shed", "dorms"],
        "helicopter" : ["outside-heli-upper", "outside-heli-bottom"],
        "outside-heli-bottom" : ["helicopter", "outside-dog-shed"],
        "dorms" : ["outside-heli-upper", "restroom", "middle-hallway"],
        "restroom" : ["dorms"],
        "garage" : ["outside-shed", "upper-hallway"],
        "upper-hallway" : ["garage", "middle-hallway", "lounge", "laboratory"],
        "middle-hallway" : ["mini-storage", "dorms", "upper-hallway", "lounge"],
        "mini-storage" : ["middle-hallway"],
        "lounge" : ["middle-hallway", "upper-hallway", "lower-hallway", "kitchen"],
        "lower-hallway" : ["lounge", "storage", "outside-dog-shed"],
        "outside-dog-shed" : ["outside-heli-bottom", "dog-shed", "lower-hallway"],
        "storage" : ["lower-hallway"],
        "kitchen" : ["lounge"],
        "laboratory" : ["upper-hallway"],
        "dog-shed" : ["outside-dog-shed"]}
    return Rooms


def room_abbreviations():
    abbreviationsdict = {
        "ds" : "dog-shed",
        "h" : "helicopter",
        "lh" : "lower-hallway",
        "ms" : "mini-storage",
        "rm" : "restroom",
        "st" : "storage",
        "sh" : "shed",
        "k" : "kitchen",
        "d" : "dorms",
        "l" : "lounge",
        "g" : "garage",
        "mh" : "middle-hallway",
        "uh" : "upper-hallway",
        "lab" : "laboratory",
        "ods" : "outside-dog-shed",
        "ohb" : "outside-heli-bottom",
        "ohu" : "outside-heli-upper",
        "os" : "outside-shed",
        "r" : "restroom",
        "ohr" : "outside-heli-bottom"
    }
    return abbreviationsdict


async def delete_and_clone_room_channels(ctx):
    rooms_list = []
    private_rooms_list = []
    start = time.time()
    room_categories = ["Outside", "Facility"]
    
    #Get Players 1 and Players 2 categories
    private_channels_category = discord.utils.get(ctx.message.guild.categories, name = "Players 1")
    
    for category in ctx.message.guild.categories:
        if category.name in room_categories:
            for channel in category.text_channels:
                if channel.name[0] == "_":
                    room = await replace_channel_w_clone_and_delete(latestroom_channel)
                    roomitems = await replace_channel_w_clone_and_delete(channel)

                    for role in ctx.guild.roles:
                        if strip(role.name) == latestroom_channel.name:
                            room_role = role
                    
                    roomclass = await Room.create(room, roomitems, room_role)
                    rooms_list.append(roomclass)
                else:
                    latestroom_channel = channel
    
    channel_names = ["player-1", "player-2", "player-3", "player-4", 
    "player-5", "player-6","player-7","player-8","player-9"]
    
    private_channels_list = []
    
    for channel_name in channel_names:
        for private_channel in private_channels_category.text_channels:
            if private_channel.name == channel_name:
                new_private_channel = await private_channel.clone()
                await private_channel.delete()
                private_channels_list.append(new_private_channel)
    time_spent = time.time() - start
    return rooms_list, private_channels_list, time_spent


async def is_profession(player_type, Profession_name):
    DispatchedInfo = await openDispatchedInfojson()
    character_name = player_type.character_name
    if Profession_name in DispatchedInfo["Characters"][character_name]["Abilities"]:
        return True
    return False


def remove_duplicates_from_list(list_with_duplicates):
    return list(dict.fromkeys(list_with_duplicates))


def formating_string(starter_string, lst, aoranactivated = False):
    
    if len(lst) == 0:
        return "Empty"
    
    if len(lst) == 1:
        if aoranactivated:
            return starter_string + aORan(lst[0])
        return starter_string + str(lst[0])
    
    if len(lst) == 2:
        if aoranactivated:
            return starter_string + aORan(lst[0]) + " and " + aORan(lst[1])
        return starter_string + lst[0] + " and " + lst[1]
    
    for i in range(len(lst)):
        if i == len(lst) - 1:
            if aoranactivated:
                starter_string += (f'and {aORan(lst[i])}.')
            else:
                starter_string += (f'and {lst[i]}.')
        else:
            if aoranactivated:
                starter_string += (f'{aORan(lst[i])}, ')
            else:
                starter_string += (f'{lst[i]}, ')
    #starter_string has now been modified to the formated string. returns this string.
    end_string = starter_string
    return end_string


def aORan(word):
    lower_case_word = ("".join(word)).lower()
    if lower_case_word[0] in ['a', 'e', 'i', 'o', 'u']:
        return f'an {word}'
    return f'a {word}'


async def remove_member_roles(ctx, ADMINROLENAME = ADMINROLENAME, write_out = True):
    adminrole = discord.utils.get(ctx.guild.roles, name = ADMINROLENAME)
    #ListComprehension
    [await member_type.edit(roles = []) 
        for member_type in ctx.guild.members 
        if (not adminrole in member_type.roles) and (not member_type.bot)]
    if write_out:
        await ctx.send("All members besides admins and bots had their roles removed.")


def create_random_color(RGB = None):
    if RGB:
        return discord.Color.from_rgb(add_or_remove_15_to_rgb_value(RGB[0]), add_or_remove_15_to_rgb_value(RGB[1]), add_or_remove_15_to_rgb_value(RGB[2]))
    #random
    RGB = [int(180*random.random()) for i in range(3)]
    lstrgb = [i for i in RGB]
    return discord.Color.from_rgb(lstrgb[0], lstrgb[1], lstrgb[2])


def add_or_remove_15_to_rgb_value(rgb_value):
    rgb_value += (15 if random.random() > 0.5 else -15)
    
    if rgb_value < 1:
        rgb_value = 5
    
    elif rgb_value > 180:
        rgb_value = 175
    
    return rgb_value


def find_invoked_command(ctx):
    return ctx.invoked_with


def player_in_shape_to_play(player_type):
    return not (player_type.is_dead or player_type.is_injured or player_type.is_tied)

def player_not_in_shape_to_play(player_type):
    return not player_in_shape_to_play(player_type)

def check_player_can_play_and_not_idle(player_type):
    if (player_not_in_shape_to_play(player_type) or player_type.has_escaped or player_type.idle or not player_type.can_play):
        return False
    return True

def check_player_can_play(player_type):
    if (player_not_in_shape_to_play(player_type) or player_type.has_escaped or not player_type.can_play):
        return False
    return True












