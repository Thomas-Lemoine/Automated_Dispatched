import discord, json, time, os, asyncio, random
from discord.ext import commands,tasks, menus
from class_objects import Confirm, MyMenu, Room, Character, Item, Player, Body, Entity
from Auto_Disp_functions import *
from dotenv import load_dotenv
load_dotenv()


token = os.getenv('TOKEN')
intents = discord.Intents().all()

bot = commands.Bot(command_prefix = ".", intents = intents, activity= discord.Game("Running from the Entity"), owner_id = 399565895946469397, description = "Do .info for information about Dispatched.")

#GlobVar:
LOGSCHANNELNAME = "logs"
ADMINROLENAME = "Host"
bot.rooms = {}
bot.Characters = {}
bot.items = (["FlameT", "FlameT", "Axe", "Axe", "Axe", "Fuel", "Fuel", "Fuel", "Test", "Mop", "Rope", "Rope", "Rope", "EngineP"], ["Fuel Barrel", "Fuel Barrel"])
bot.Players = {}
bot.finishedchangedallavatars = False
bot.turn = 0
bot.requests = {}#{player_type : [function_name, (tuple of arguments)],etc.}

"""
EVENTS
""" 

@bot.event
async def on_ready():
    print("Bot is ready.")

@bot.event
async def on_member_join(member):
    print(f'{member} has joined the server {member.guild.name}.')
    logs_channel = discord.utils.get(member.guild.text_channels, name = LOGSCHANNELNAME)
    if member.bot:
        await logs_channel.send(f"The bot {member.mention} has joined.")
    else:
        await logs_channel.send(f"{member.mention} has joined. They will be part of the next game.")

@bot.event
async def on_member_remove(member):
    print(f'{member} has left the server {member.guild.name}.')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await (await ctx.send(f"The command '{ctx.message.content}' doesn't exist.")).delete(delay = 3)
        await ctx.message.delete()
    else:
        raise error


""" TASKS """
@tasks.loop(seconds = 60)
async def check_changed_avatar(guild: discord.Guild, avatars_dict):
    admin_role = discord.utils.get(guild.roles, name = ADMINROLENAME)
    players_member_type = [player_member for player_member in guild.members if (not admin_role in player_member.roles) and (not player_member.bot)]
    current_avatars_dict = {player_member.name:player_member.avatar_url for player_member in players_member_type}
    unchanged_avatars_num = 0

    for i,player_member in enumerate(players_member_type):
        if current_avatars_dict[player_member.name] == avatars_dict[player_member.name]:
            player_type = bot.Players[player_member.name]
            await player_type.private_channel.send(f'{player_member.mention} - Please change your profile picture. The game is about to start.')
            unchanged_avatars_num += 1
    
    if unchanged_avatars_num == 0:
        for player_type in bot.Players.values():
            await player_type.private_channel.send("Everyone has changed their pfps. The game is about to start...")
        
        await asyncio.sleep(1)
        check_changed_avatar.stop()
    
    else:
        for player_type in bot.Players.values():
            await player_type.private_channel.send(f"({unchanged_avatars_num}/{len(players_member_type)}) players haven't changed their pfp yet.")



"""
TEST
"""
#nothing here...

"""

GAME OVERARCHING COMMANDS

"""

async def _initialization(ctx, skip_avatar_changing_bool):
    t0 = time.time()
    inline_bool = True

    #Load DispatchedInfo
    DispatchedInfo = await openDispatchedInfojson()

    #Initialize main Embed
    title = "Setup (In progress)"
    if skip_avatar_changing_bool:
        title = "Setup (The game is in speedup mode)"
    desc = "Dispatched is currently initializing..."
    thumbnail = DispatchedInfo["Information"]["Images"]["Dispatched_image"]
    setup_embed = discord.Embed(
        title = title,
        description = desc,
        color = create_random_color()
        ).set_image(url = thumbnail)

    #Send the embed and save the message so it can be edited easily later on
    setup_embed_msg = await ctx.send(embed = setup_embed)

    #Removing everyone's roles
    await remove_member_roles(ctx, write_out = False)
    await setup_embed_msg.edit(embed = setup_embed.add_field(
        name = "Deleting roles...",
        value = f"All member roles were deleted.",
        inline = inline_bool))
    
    """Deleting and cloning all channels and adding a blank
    embed for each RoomItems channel. Saves the list of all 
    Room classes, the list of all Channel types for the private 
    channels (in order) and the time this function took to complete."""
    rooms_list, private_channels_list, time_spent = await delete_and_clone_room_channels(ctx)
    await setup_embed_msg.edit(embed = setup_embed.add_field(
        name = "Recreating all channels...",
        value = f"...took {round(time_spent,1)} seconds.",
        inline = inline_bool))
    
    #creating the dictionary for the rooms
    for room in rooms_list:
        bot.rooms[room.name] = {
            "Room" : room,
            "Players" : [],
            "Items" : [],
            "Bodies" : []
            }

    #A list of all the room names to be able to easily
    #cycle through and see all their names
    room_names_list = [room for room in bot.rooms.keys()]

    #Scattering Items:
    channels_with_items = scrambled(random.sample(room_names_list, len(bot.items[0])))

    for i in range(len(bot.items[0])):
        item = bot.items[0][i]
        room_class = bot.rooms[channels_with_items[i]]["Room"]
        bot.rooms = await room_class.add_item_to_room(Item.create(item, pickable=True), bot.rooms)
    
    #Fuel Barrels:
    fuels_list = scrambled(bot.items[1])
    fuel_available_rooms = ["garage", "shed", "outside-shed", "outside-heli-upper",
    "outside-heli-bottom", "outside-dog-shed", "storage"]
    fuel_filled_rooms = random.sample(fuel_available_rooms, len(fuels_list))
    for i in range(len(fuels_list)):
       item = fuels_list[i]
       room_class = bot.rooms[fuel_filled_rooms[i]]["Room"]
       bot.rooms = await room_class.add_item_to_room(Item.create(item, pickable=True), bot.rooms)
    
    await setup_embed_msg.edit(embed = setup_embed.add_field(
        name = "Items",
        value = "Items were scattered around the map!",
        inline = inline_bool))
    
    #Players :
    admin_role = discord.utils.get(ctx.guild.roles, name = ADMINROLENAME)
    players_list = scrambled([player for player in ctx.guild.members
        if (not admin_role in player.roles) and (not player.bot)])
    players_name_list = [player.name for player in players_list]
    number_of_players = len(players_name_list)

    used_private_channels = scrambled(private_channels_list[:number_of_players])

    await setup_embed_msg.edit(embed = setup_embed.add_field(
        name = "Participating members : ",
        value = '\n'.join([f'{Player.mention} - {Player.name}' for Player in players_list]),
        inline = inline_bool))
    
    #All Character names
    characters_list = []
    for character_name in DispatchedInfo["Characters"].keys():
        character_type = await Character.create(character_name, DispatchedInfo)
        characters_list.append(character_type)
        bot.Characters[character_name] = character_type
    initial_used_character_types = scrambled(random.sample(characters_list, number_of_players))
    initial_used_room_names = scrambled(random.sample(room_names_list, number_of_players))
    initial_used_rooms = [bot.rooms[roomname]["Room"] for roomname in initial_used_room_names]

    

    """Give players their private channel, starting room,
    characters and nicknames. Initializing Player classes and 
    adding them to bot.rooms"""
    for i in range(number_of_players):
        member_type = players_list[i]
        private_channel_type = used_private_channels[i]
        Room_type = initial_used_rooms[i]
        character_type = initial_used_character_types[i]
        player_type = await Player.create(
            ctx, 
            member_type,
            private_channel_type,
            Room_type, 
            character_type)
        bot.Players[player_type.name] = player_type
        bot.rooms[player_type.Room.name]["Players"].append(player_type)

    #Giving Entity to a random player
    Entity_player_type = random.choice([Player for player, Player in bot.Players.items()])
    Entity_embed = discord.Embed(
        title = "The Entity",
        description = "\n".join(DispatchedInfo["Entity"]["Abilities"]),
        color = Entity_player_type.change_embed_color()
        ).set_image(url = DispatchedInfo["Entity"]["image_url"])
    await Entity_player_type.give_entity_to_player(Entity_embed)

    players_info_initialization = {
        player_name:(f"{player_type.member_type.mention} was placed in {player_type.room_role}. They're in the private channel {player_type.private_channel.mention} and were given the character {player_type.character_type.name}.") 
    for player_name, player_type in bot.Players.items()
    }
    #setup_embed.add_field(name = "Characters information", value = "\n".join(players_info_initialization), inline = inline_bool)
    for player_name in players_info_initialization.keys():
        setup_embed.add_field(name = player_name, value = players_info_initialization[player_name], inline = inline_bool)
    
    entity_string = f'{Entity_player_type.member_type.mention} - __{Entity_player_type.name} is the Entity.__'
    await setup_embed_msg.edit(
        embed = setup_embed.add_field(
            name = "The Entity was picked",
            value = entity_string,
            inline = inline_bool
            )
        )
    
    #Send completion messages
    await setup_embed_msg.edit(
        embed = setup_embed.add_field(
            name = "Placing players in ...",
            value = "... their private channel\n... their starting room",
            inline = inline_bool))
    
    await setup_embed_msg.edit(
        embed = setup_embed.add_field(
            name = "Giving players ...",
            value = "... their Characters' embeds\n... their nicknames",
            inline = inline_bool))
    
    await setup_embed_msg.edit(
        embed = setup_embed.add_field(
            name = "Setup Complete !",
            value = f"Ask players to change their profile pictures !",
            inline = inline_bool))
        
    #Modifying the title
    modified_title = f"Setup (Complete !)"
    setup_embed_dict = setup_embed.to_dict()
    setup_embed_dict["title"] = modified_title
    setup_embed_dict["description"] = f"The setup took {round(time.time() - t0,1)} seconds."
    setup_embed = discord.Embed.from_dict(setup_embed_dict)
    await setup_embed_msg.edit(embed = setup_embed)
    return 
    

@commands.has_role(ADMINROLENAME)
@bot.command(name = "start")
async def maingame(ctx):
    question_str = "Is this an actual game ?"
    
    skip_avatar_changing_bool = False
    
    if not await ask_yes_no(ctx, question_str):
        skip_avatar_changing_bool= True
    
    
    bot.turn = 0
    game_is_finished = False
    

    admin_role = discord.utils.get(ctx.guild.roles, name = ADMINROLENAME)
    players_member_type = [player_member for player_member in ctx.guild.members if (not admin_role in player_member.roles) and (not player_member.bot)]
        

    await _initialization(ctx, skip_avatar_changing_bool)

    if not skip_avatar_changing_bool:
        avatars_dict = {player_member.name:player_member.avatar_url for player_member in players_member_type}
        await check_changed_avatar.start(ctx.guild, avatars_dict)
        await asyncio.sleep(0.1)
    
    await asyncio.sleep(0.1)

    while not game_is_finished:
        bot.turn += 1
        t0 = time.time()
        bot.requests = {}

        #turn_message_embed
        for player_type in bot.Players.values():

            if player_type.is_dead:
                pass
            
            elif player_type.idle:
                player_type.set_can_play_true()
                await player_type.private_channel.send(f"*You are skipping turn {bot.turn}. Do .offidle to stop skipping turns.*")
            
            elif not player_in_shape_to_play(player_type):
                await player_type.private_channel.send(f"Your turn {bot.turn} is being skipped because you are {'tied up' if player_type.is_tied else 'injured'}.")

            else:
                player_type.set_can_play_true()
                player_turn_message_embed = await get_turn_message_embed(player_type)
                await player_type.private_channel.send(embed = player_turn_message_embed)
        
        time_increment = 5
        turn_seconds_counter = 20
        turn_max_length_in_seconds = 180
        turn_min_length_in_seconds = 50
        await asyncio.sleep(turn_seconds_counter)
        
        """Check if all players have played. If they haven't all played, 
        do nothing until 1m30 into the round, and thereafter send messages 
        to those players asking them to play. After 3min, move to the next turn.
        CHANGED
        """
        you_havent_played_string = lambda player_type: f"{player_type.member_type.mention} You haven't played yet. Do .skip if you wish to skip this round and .idle if you wish to skip all turns for some time."
        
        while ((not all_have_played()) or (turn_seconds_counter <= turn_min_length_in_seconds)):
            
            if turn_seconds_counter == 90:
                players_who_havent_played_list = find_players_who_havent_played_yet()
                
                [await player_type.private_channel.send(you_havent_played_string(player_type)) for player_type in players_who_havent_played_list]

            #At 3min, move on no matter what.
            if turn_seconds_counter >= turn_max_length_in_seconds - 10:
                players_who_havent_played_list = find_players_who_havent_played_yet()
                
                for player_type in players_who_havent_played_list:
                    await player_type.private_channel.send("You are now idle. Do .offidle when you are back.")

                    player_type.idle = True
                    player_type.set_can_play_false()
                
                await asyncio.sleep(10)
                
                break #out of the while loop.
            
            await _run_new_request()

            await asyncio.sleep(time_increment)
            turn_seconds_counter += time_increment

        for player_type in bot.Players.values():
            player_type.set_can_play_false()
        
        print(f'Turn {bot.turn} took {time.time() - t0} seconds to go through.')
        await asyncio.sleep(1)

        #Check if the game is over, and sets that to the game_is_finished bool
        game_is_finished = return_true_if_game_is_over()
        if game_is_finished:
            print("GAME OVER")
            [await player_type.private_channel.send("GAME OVER!") for player_type in bot.Players.values() if not player_type.is_dead]
        
        
async def _run_new_request():
    #bot.requests = {player_name : [player_type, function_name, *args],etc.}
    
    if not any(bot.requests.keys()):
        return
    
    #print(bot.requests)

    random_requesting_player_name_chosen = random.choice(list(bot.requests.keys()))
    player_name, lst_player_func_args = random_requesting_player_name_chosen, bot.requests[random_requesting_player_name_chosen]
        
    player_type = lst_player_func_args[0]
    func_name = lst_player_func_args[1]
    args_lst = None

    if len(lst_player_func_args) > 2:
        args_lst = lst_player_func_args[2:len(lst_player_func_args)]

    await _run_move_based_on_func(player_name, player_type, func_name, args_lst)

    return

async def _run_move_based_on_func(player_name, player_type, func_name, args_lst):
    
    move_successful_bool = False
    
    if type(player_name) != str or type(player_type) != Player or type(func_name) != str:
        raise KeyError
    
    """MAIN COMMANDS"""
    if func_name in ['move', 'm']:
        new_room_name = args_lst[0]
        await _run_move_to_room(player_type, new_room_name)
        move_successful_bool = True
    
    elif func_name in ["pick","p"]:
        item_type = args_lst[0]
        await _run_pick_item(player_type,item_type)
        move_successful_bool = True
    
    elif func_name in ["drop", "d"]:
        item_type = args_lst[0]
        await _run_drop_item(player_type, item_type)




    if move_successful_bool and player_type.idle:
        player_type.idle = False
        await player_type.private_channel.send("Since you just played, you have gone off idle.")   



"""
MOVES
"""

"""
PRIORITY MOVES
"""

"""SKIP TURN"""

@bot.command(name = 'skip')
async def _skip_turn(ctx):
    
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
    
    if check_player_can_play_and_not_idle(player_type) == False:
        await player_type.private_channel.send("You don't need to skip the turn in this state.")
        return
    
    player_type.set_can_play_false()
    remove_player_requests(player_type)
    

    await player_type.private_channel.send("You have skipped this turn.")

"""SUICIDE"""

@bot.command(name = 'suicide')
async def _suicide(ctx):
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return

    deadrole = discord.utils.get(ctx.guild.roles, name = "Dead")
    bot.rooms = await player_type.kill(deadrole, bot.rooms, with_messages = True)

    player_type.set_can_play_false()
    remove_player_requests(player_type)


"""
REQUEST MOVES
"""

"""MOVE_TO_ROOM"""

@bot.command(name = "move", aliases = ["m", "movetoroom"])
async def _move(ctx, *new_room_name):
    new_room_name = "".join(new_room_name)

    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
    
    if not (new_room_name := await can_move_to(player_type, new_room_name)):
        await ctx.message.delete()
        return

    #can_therefore_move
    await store_request(ctx, player_type, new_room_name)

async def can_move_to(player_type, new_room_name):
    
    abbreviations_dict = room_abbreviations()
    if new_room_name in abbreviations_dict:
        new_room_name = abbreviations_dict[new_room_name]
    
    allowed_rooms_dict = get_allowed_rooms_dict()

    #Don't let the player move if they can't move.
    if not check_player_can_play(player_type):
        message = await player_type.private_channel.send(f"**You currently can't move, {player_type.character_name}**")
        await message.delete(delay = 10)
        return
    
    #stops the function if the input room isn't valid
    if new_room_name not in bot.rooms:
        message = await player_type.private_channel.send(f"**The room {new_room_name} doesn't exist, {player_type.character_name}. Do .roominfo to see which rooms are available.**")
        await message.delete(delay = 10)
        return

    #If the new room isn't valid, error message
    if new_room_name not in allowed_rooms_dict[player_type.Room.name]:
        message = await player_type.private_channel.send(f"**Please send a valid room to move to, {player_type.character_name}**")
        await message.delete(delay = 10)
        return
    
    return new_room_name

async def _run_move_to_room(player_type, new_room_name):

    if not await can_move_to(player_type, new_room_name):
        await player_type.private_channel.send("You were prevented from moving!")

    #If everything is good, moving things around
    new_Room = bot.rooms[new_room_name]['Room']
    bot.rooms = await player_type.move_room(new_Room, bot.rooms, with_messages = True)

    player_type.set_can_play_false()
    remove_player_requests(player_type)
    return

"""PICK ITEM"""

@bot.command(name = 'pick', aliases = ['p'])
async def _pick_item(ctx, *item_name):
    item_name = " ".join(item_name)

    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return

    if not (item_type := await find_item_type_in_player_room(player_type, item_name)):
        await ctx.message.delete()
        return

    if not await player_can_pick_item(player_type, item_type):
        await ctx.message.delete()
        return
    
    await store_request(ctx, player_type, item_type)
    
async def player_can_pick_item(player_type, item_type):
    if not check_player_can_play(player_type):
        message = await player_type.private_channel.send("You can't play at the moment.")
        await message.delete(delay = 15)
        return False
    
    if player_type.is_max_weight():
        message = await player_type.private_channel.send("Your inventory is full.")
        await message.delete(delay = 15)
        return False

    if item_type not in bot.rooms[player_type.Room.name]["Items"]:
        message = await player_type.private_channel.send(f"The item '{item_type.name}' is not in the room.")
        await message.delete(delay = 15)
        return False
    
    if item_type.name == "Fuel Barrel":
        message = await player_type.private_channel.send(f"You cannot pick the Fuel Barrel. You can only use it to pick items up.")
        await message.delete(delay = 15)
        return False

    #else:
    return True

async def find_item_type_in_player_room(player_type, item_name):
    
    items_in_room = bot.rooms[player_type.Room.name]["Items"]

    if item_name not in [item_type.name for item_type in items_in_room]:
        message = await player_type.private_channel.send(f"The item '{item_name}' is not in the room.")
        await message.delete(delay = 15)
        return
    
    valid_item_type_list = [item_type for item_type in items_in_room if item_type.name == item_name]

    

    return random.choice(valid_item_type_list)
    
async def _run_pick_item(player_type, item_type):
    if not await player_can_pick_item(player_type, item_type):
        return
    await player_type.add_item_to_inv(item_type, bot.rooms)
    player_type.set_can_play_false()
    remove_player_requests(player_type)
    return


"""DROP ITEM"""
@bot.command(name = 'drop', aliases = ['d'])
async def _drop_item(ctx, *item_name):
    item_name = " ".join(item_name)

    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return

    if not (item_type := await find_item_type_in_player_inv(player_type, item_name)):
        await ctx.message.delete()
        return
    
    if not await player_can_drop_item(player_type, item_type):
        await ctx.message.delete()
        return
    
    await store_request(ctx, player_type, item_type)
    
async def _run_drop_item(player_type, item_type):
    if not await player_can_drop_item(player_type, item_type):
        return
    await player_type.drop_item_from_inv(item_type, bot.rooms)
    
    player_type.set_can_play_false()
    
    remove_player_requests(player_type)
    return

async def find_item_type_in_player_inv(player_type, item_name):
    valid_item_type_list = []
    
    for item in player_type.items:
        if item.name == item_name:
            valid_item_type_list.append(item)
    
    if not any(valid_item_type_list):
        message = await player_type.private_channel.send(f"The item '{item_name}' is not in your inventory.")
        await message.delete(delay = 15)
        return
    
    return random.choice(valid_item_type_list)

async def player_can_drop_item(player_type,item_type):
    if not check_player_can_play(player_type):
        message = await player_type.private_channel.send("You can't play at the moment.")
        await message.delete(delay = 15)
        return False
    
    if item_type not in player_type.items:
        message = await player_type.private_channel.send(f"The item '{item_type.name}' is not in your inventory.")
        await message.delete(delay = 15)
        return False
    
    #else:
    return True

"""
Utility commands
"""

@bot.command(name = "info")
async def _info(ctx, *, infotype = None):
    inline_bool = False
    
    if infotype:
        infotype = "".join(infotype)
    DispatchedInfo = await openDispatchedInfojson()
    
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return

    #.info <word> for more specific information        
    if infotype in [key for key in DispatchedInfo["Information"].keys() if not (key == "Images")]:
        embed = discord.Embed(
            description = DispatchedInfo["Information"][infotype],
            color = (player_type.change_embed_color())
            )
        if infotype == "setting":
            embed.set_image(url = DispatchedInfo["Information"]["Images"]["setting-banner"])
    
    elif infotype in DispatchedInfo["Information"]["Images"].keys():
        embed = discord.Embed(
            title = infotype,
            color = player_type.change_embed_color()
            ).set_image(url = DispatchedInfo["Information"]["Images"][infotype])
    
    elif infotype == "abilities":
        embed = discord.Embed(
            title = f"{player_type.character_name}'s abilities",
            color = (player_type.change_embed_color())
            ).set_author(
                name = player_type.character_name,
                icon_url = DispatchedInfo["Characters"][player_type.character_name]["image_url"]
                )

        for ability in DispatchedInfo["Characters"][player_type.character_name]["Abilities"]:
            embed.add_field(name = ability, value = DispatchedInfo["Abilities"][ability], inline = inline_bool)
        
    elif infotype == "items":
        embed = discord.Embed(
            title = f"{player_type.character_name}'s items",
            color = (player_type.change_embed_color())
            ).set_author(
                name = player_type.character_name,
                icon_url = DispatchedInfo["Characters"][player_type.character_name]["image_url"]
                )
    
        for item in player_type.items:
            embed.add_field(name = item.name, value = DispatchedInfo["Items"][item.name], inline = inline_bool)
        
    elif infotype == "Entity" and player_type.is_entity:
        entity_dict = DispatchedInfo["Entity"]
        embed = discord.Embed(
            title = infotype, 
            description= entity_dict["Description"],
            color = (player_type.change_embed_color())
            )
        for abilityname in DispatchedInfo["Entity"]["Abilities"]:
            embed.add_field(name = abilityname, value = DispatchedInfo["Abilities"][abilityname], inline = inline_bool)
    
    #Basic .info command
    elif infotype == None:
        embed = discord.Embed(
            title = "Information",
            description = f"Do .info <image-name> to see the image.\nThe images are {formating_string('',[key for key in DispatchedInfo['Information']['Images'].keys()])}.",
            color = (player_type.change_embed_color())
            )
        [
            embed.add_field(
                name = key,
                value = f"Do .info {key} for information about {key}",
                inline = inline_bool
                )
            for key in DispatchedInfo["Information"].keys() if key != "Images"
        ]

        embed.add_field(name = "abilities", value = f"Do .info abilities for information about your Character's abilities.", inline = False)
        embed.add_field(name = "items", value = f"Do .info items for information about the items you're carrying.", inline = False)
        
        if player_type.is_entity:
            embed.add_field(name = "Entity info", value = "Do .info Entity for more imformation about the Entity's abilities.", inline=False)
    
    else:
        embed = discord.Embed(
            title = "This command does not exist. Try again.",
            color = (player_type.change_embed_color())
            )

    #send the embed
    await ctx.send(embed = embed)


@bot.command(name = 'lessinfo')
async def _shortenturnmessage(ctx):
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
        
    player_type.default_turn_embed = False
    
    await player_type.private_channel.send("Your turn messages will now be shorter and stop displaying the room's info.")


@bot.command(name = 'moreinfo')
async def _lengthenturnmessage(ctx):
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
        
    player_type.default_turn_embed = True
    
    await player_type.private_channel.send("Your turn messages will now contain the room's information.")


@bot.command(name = 'roominfo', aliases = ['inforoom', 'room_info'])
async def _roominfo(ctx):
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
    
    info_in_room = discord.Embed(
        title = f"Information about the {' '.join(player_type.Room.name.split('-'))} :",
        color = (player_type.change_embed_color())
    )

    info_in_room = add_room_info_fields(info_in_room, player_type)

    await player_type.private_channel.send(embed = info_in_room)


@bot.command(name = "idle")
async def _go_idle(ctx):
    
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
    
    if player_type.idle == True:
        await player_type.private_channel.send("Unvalid command. Maybe you meant .offidle ?")
        return
    
    player_type.idle = True
    #player_type.set_can_play_false()

    await player_type.private_channel.send("You have now gone idle. Do .offidle to go off idle mode such that you can get turn information.")

@bot.command(name = 'offidle')
async def _go_off_idle(ctx):
    #Define player_type, and get out of the function if the user is not a player or in a private_channel.
    if not (player_type := await find_player_type(ctx)):
        return
    
    if player_type.idle == False:
        await player_type.private_channel.send("Invalid command. Maybe you meant .idle ?")
        return

    player_type.idle = False
    await player_type.private_channel.send("You have now gone off idle.")




"""
FUNCTIONS
"""


async def find_player_type(ctx):
    Players_dict = bot.Players
    player_type = None
    for player_type_in_dict in Players_dict.values():
        if player_type_in_dict.private_channel == ctx.message.channel:
            player_type = player_type_in_dict
            break
    if player_type == None:
        await ctx.message.delete()
        if ctx.author.name in Players_dict:
            player_type = Players_dict[ctx.author.name]
            await player_type.private_channel.send(f"{player_type.member_type.mention}, please keep commands in your private channel.")
        else:
            channel = discord.utils.get(ctx.guild.text_channels, name= "bot-testing")
            await channel.send(f"{ctx.author.mention} Keep the commands valid, thx.")
            return False
    return player_type

async def store_request(ctx, player_type, args):
    player_name = player_type.name
    
    if player_name in bot.requests:
        del bot.requests[player_name]
    
    bot.requests[player_name] = [player_type, ctx.invoked_with]
    [bot.requests[player_name].append(arg) for arg in args] if type(args) == list else bot.requests[player_name].append(args)
    
    await player_type.private_channel.send(f'Your request was stored.', delete_after = 20)
    
    return

def remove_player_requests(player_type):
    if player_type.name in bot.requests:
        del bot.requests[player_type.name]
    return

def return_true_if_game_is_over():
    
    players_type_list = bot.Players.values()
    for player_type in players_type_list:
        if player_type.is_entity:
            entity_player = player_type

    dead_players_list = [player_type for player_type in players_type_list if player_type.is_dead]
    escaped_players_list = [player_type for player_type in players_type_list if player_type.has_escaped]

    #If anyone has escaped with the heli or there's only one person alive
    if any(escaped_players_list) or (len(dead_players_list) >= len(players_type_list) - 1):
        return True
    
    else:
        return False

def add_room_info_fields(embed, player_type):
        
    Room_dict = bot.rooms[player_type.Room.name]
    Room_type = Room_dict["Room"]
    Room_name = Room_type.name
    players_in_room = [player for player in Room_dict['Players'] if player != player_type]
    items_in_room = Room_dict["Items"]
    Bodies = Room_dict["Bodies"]
    player_items = [item for item in player_type.items]
    allowed_rooms = get_allowed_rooms_dict()
    reverse_abbrev_dict = {value:key for key,value in room_abbreviations().items()}

    embed.add_field(
        name = "The adjacent rooms are :" if len(allowed_rooms[Room_name]) > 1 else "The adjacent room is : ",
        value = formating_string("", [f'{room} ({reverse_abbrev_dict[room]})' for room in allowed_rooms[Room_name]]),
        inline = False)

    if any(player_items):
        embed.add_field(
            name = "You are holding onto : ",
            value = formating_string("", [item.name for item in player_items], True),
            inline = False)

    if any(players_in_room):
        embed.add_field(
            name = "The players in the room are : " if len(players_in_room) > 1 else "The player in the room is : ",
            value = formating_string("", [f'{player.recreate_nickname()}' for player in players_in_room]),
            inline = False)
    
    if any(items_in_room):
        embed.add_field(
            name = "The items in the room are : " if len(items_in_room) > 1 else "The item in the room is : ",
            value = formating_string("",[item.name for item in items_in_room], True),
            inline = False)
    
    if any(Bodies):
        embed.add_field(
            name = "The bodies in the room are : " if len(Bodies) > 1 else "The body in the room is : ",
            value = formating_string("", [body.name for body in Bodies]),
            inline = False)
    
    if any([player.can_be_carried for player in players_in_room]):
        embed.add_field(
            name = "These players can be carried : " if len([player.can_be_carried or player.is_tied for player in players_in_room]) > 1 else "This player can be carried : ",
            values = formating_string("", [f'{player.character_name} ({("TIED UP" if (player.is_tied != None) else "INJURED")})' for player in players_in_room if player.can_be_carried]), 
            inline = False)
    
    return embed

async def get_turn_message_embed(player_type):
    turn = bot.turn
    Room_dict = bot.rooms[player_type.Room.name]
    Room_type = Room_dict["Room"]
    Room_name = Room_type.name
    players_in_room = [player for player in Room_dict['Players'] if player != player_type]
    items_in_room = Room_dict["Items"]
    Bodies = Room_dict["Bodies"]
    player_items = [item for item in player_type.items]
    all_items_in_room = items_in_room + player_items + [[item for item in player.items] for player in players_in_room]
    fuelables = []
    allowed_rooms = get_allowed_rooms_dict()
    desc = (f'Do __.roominfo__ to get information about the {Room_name}.' if not player_type.default_turn_embed else f'You are in the {Room_name}') + '\n\n'
    desc += "**Below is the list of your available moves :**"
    
    #Move to another room
    desc += "\n__.move <room's name>__ to move to an adjacent room."

    #Pick an item in a room
    if any(items_in_room) and not player_type.is_max_weight():
        desc += f"\n__.pick <item's name>__ to pick an item in the room."

    #Chop someone with an axe
    if any("Axe" == item.name for item in player_items) and any(players_in_room):
        desc += "\n__.axe <player's name>__ to attack someone with an Axe."

    #Tie someone up
    if any(players_in_room) and any("Rope" == item.name for item in player_items):
        desc += "\n__.tie <player's name>__ to try tying someone up."
 
    #Attack someone with your fists
    if any(players_in_room):
        desc += "\n__.attack <player's name>__ to try beating someone up."
    
    #Flame someone with FlameT
    if any("FlameT" == item.name and item.contains > 0 for item in player_items) and any(players_in_room):
        desc += "\n__.flame <player's name>__ to Flame one of the players in the room."
    
    #Drop an item in a room
    if any(player_items):
        desc += "\n__.drop <item's name>__ to drop an item in the room."

    #Repair the EngineP
    if (Room_name == "garage" 
    and any(item.name == "EngineP" and not item.isRepaired for item in player_items) 
    and await is_profession(player_type, "Engineer")):
        desc += "\n__.repair__ to repair the Engine."

    #Repair the heli with the repaired Engine
    if Room_name == "helicopter":
        fuelables.append("helicopter")
        if any(item.name == "EngineP" and item.isRepaired for item in player_items):
            desc += "\n__.repairHeli__ to repair the heli."

    #Fuelable items in the room
    [fuelables.append([item.name for item in player.items if item.isFillable]) for player in players_in_room]
    fuelables.append([item.name for item in player_type.items if item.isFillable])

    #Fill an item with the fuel in your Fuel item
    if any(item.name == "Fuel" and item.contains > 0 for item in player_items) and any(fuelables):
        desc += "\n__.fill <item's name>__ to fuel another item within the room with your Fuel. If many such items are in the room, you can do .fill <item's name> <player's name (or floor)> to specify whose <item's name> you're filling up."

    #Fuel EFuel with Fuel Barrel
    if (any(item.name == "Fuel Barrel" and item.contains > 0 for item in items_in_room) 
        and any(item.name == "EFuel" for item in player_items)):
            desc += "\n__.fillEFuel__ to fill your EFuel using a Fuel Barrel."
    
    #give someone else your item
    if any(player_items) and any(players_in_room):
        desc += "\n__.give <item's name> <player's character name>__ to give one of the players in the room one of your items. They may refuse to take the item if they wish, in which case you'll keep it in hand."

    #Fly away in the heli when it's fueled and repaired
    if any("Fueled Heli" == item.name for item in items_in_room) and any("Repaired Heli" == item.name for item in items_in_room):
        if await is_profession(player_type, "Pilot"):
            desc += "\n__.fly__ to fly away in the heli. Careful : If someone enters the helicopter before you leave, they will leave with you."
        else:
            desc += "\n__.fly__ to fly away in Heli. Be careful : You are NOT a pilot. Your chances of successful escape will be greatly reduced."

    #clean an item using the mop in the kitchen
    if Room_name == "kitchen" and any("Mop" == item.name and item.washed for item in player_items):
        desc += "\n__.clean <item's name>__ to clean an item within the kitchen."

    #Wet the mop:
    if Room_name == "kitchen" and any("Mop" == item.name and not item.washed for item in player_items):
        desc += "\n__.wet__ to wet the Mop so it can be used again."
    
    #Wash a test in the restroom
    if Room_name == "restroom" and any(item.name == "Test" for item in player_items):
        desc += "\n__.wash__ to clean the test in your inventory."

    #test a player
    if any(item.name == "Test" and item.washed for item in player_items) and any(players_in_room) and await is_profession(player_type, "Scientist"):
        desc += "\n__.test <player's name>__ to test a player."

    #untie someone
    if any(player.can_be_carried and player.is_tied != None for player in players_in_room):
        desc += "\n__.untie <player's name>__ to untie a player."
    
    #pick a body
    if player_type.weight == 0 and any(body.is_pickable for body in Bodies):
        desc += "\n__.drag <body's character's name>__ to carry a character's dead body. Anytime you'll move to a new room, the body will come with you."

    #pick an injured or tied player
    if not player_type.is_max_weight() and player_type.is_carrying == None and any(player.can_be_carried for player in players_in_room): 
        desc += "\n__.carry <player's name>__ to carry a player around. They must be injured or tied up."

    #Drop a player or body one is carrying
    if player_type.is_carrying != None:
        desc += f"\n__.dropB__ to drop {player_type.is_carrying.name}."

    #Steal a player's item
    if any(player.items for player in players_in_room):
        desc += f"\n__.steal <player's name> <item's name>__ to attempt to steal a player's item."
    
    #Ask player's item:
    if any(player.items for player in players_in_room):
        desc += f"\n__.request <player's name> <item's name>__ to ask a player for their item. They can refuse."
    
    #Give someone an item:
    if any(player_items) and any(players_in_room):
        desc += f"\n__.give <player's name> <item's name>__ to give a player one of your item. They can refuse."
    
    if player_type.is_entity:
       desc = get_entity_description(desc, player_type, Room_dict)

    turn_moves_embed = discord.Embed(
        title = f"Turn {turn}",
        description = desc,
        color = (player_type.change_embed_color())
    )
    
    less_or_more_info_bool = 'lessinfo to remove the room information from' if player_type.default_turn_embed else 'moreinfo to add back the room info to'
    turn_moves_embed.set_footer(text = f"Do .skip to skip the turn and .suicide to leave the game permanently.\nDo .idle to go idle (the bot won't ask you to make move).\nDo .{less_or_more_info_bool} the turn messages.")
    

    if player_type.default_turn_embed:
        turn_moves_embed = add_room_info_fields(turn_moves_embed, player_type)

    return turn_moves_embed

def get_entity_description(desc, player_type, Room_dict):
    Room_type = Room_dict["Room"]
    Room_name = Room_type.name
    players_in_room = [player for player in Room_dict['Players'] if player != player_type]
    items_in_room = Room_dict["Items"]
    Bodies = Room_dict["Bodies"]
    player_items = [item for item in player_type.items]
    Entity_type = player_type.entity_type
    #allowed_rooms = [key for key in get_allowed_rooms_dict().keys() if key != Room_name]

    desc += f"\n\n**Here are your Entity moves:** "

    #genetic breech an item
    if any(items_in_room) and not Entity_type.hasBreachedItem:
        desc += f"\n__.breachitem <item's name>__ to breach an item in the room. The first player to pick this item up will be infected."
    
    #genetic breech a player (they will see it)
    #nothingyet

    #genetic breech a body and assimilate a body
    if any(Bodies) and not Entity_type.hasBreachedBody:
        desc += f"\n__.breachbody <body's Character's name>__ to breach a body in the room. If you get Flamed, you can reapear in this body in a False Mortality state."
    
    if any(Bodies):    
        desc += f"\n__.assimilate <body's Character's name>__ to take a body's form. You will lose your gain their attributes and keep previous ones."

    #attic acrobat to another room
    if Entity_type.Abilitiesleft > 0 and Entity_type.isTransformed:
        desc += f"\n__.atticacrobat <room's name>__ to move to a room instantly."

    #Transform into Entity
    if not Entity_type.isTransformed:
        desc += f"\n__.transform__ to transform into the Entity." 

    #Tranform back to one of the previous Human forms
    if Entity_type.isTransformed:
        desc += f"\n__.tohuman <Character's name>__ to transform back into a human. Do this when alone in a room, or it will be visible."

    #activate Hidden Power
    if Entity_type.Abilitiesleft > 0 and not Entity_type.isTransformed and not Entity_type.hasHiddenPower:
        desc += f"\n__.enableHiddenPower__ to maximize your chances to win the next combat situation you will be faced with, when in human form. This does not count as a turn."
    
    if Entity_type.hasHiddenPower:
        desc += f"\n__.disableHiddenPower__ to disable the Hidden Power bonus. This does not count as a turn."
    
    # Maul a player
    if any(players_in_room) and Entity_type.isTransformed:
        desc += f"\n__.maul <player's name>__ to leap on a player and attempt to maul them."
        desc += f"\n__.move_and_maul <player's name>__ to leap on a player in the room, and to follow them in a different room if they manage to leave before your leap."
        
    if not Entity_type.FalseMortality:
        desc += f"\n__.FalseMortality__ to pretend to commit suicide. You will receive messages from within the room, in your private_channel."

    # Revive
    else:
        desc += f"\n__.revive__ to come back to life after False Mortality."

    #TO ADD : SMELL


    return desc

def all_have_played():
    if len(find_players_who_havent_played_yet()) == 0:
        return True
    #else
    return False

def find_players_who_havent_played_yet():
    players_can_play_list = [player_type for player_type in bot.Players.values() if check_player_can_play_and_not_idle(player_type)]

    return players_can_play_list

async def ask_yes_no(ctx, question):
    confirm = await Confirm(question).prompt(ctx)
    return confirm

"""
OK SO BASICALLY
bot.move_requests = {}
when someone does .move <place>, it checks if
they can move, it checks if that place exists, it
checks if it's valid for them (sends corresponding
error messages otherwise). If they can move there, request created for {someone : "move place"} or something.


#Every _run_<move> removes the request at the end.


"""










bot.run(token)