import math
import random
import time
from server.conf import settings
from world import rules_race, rules_skills, rules_combat
from evennia import TICKER_HANDLER as tickerhandler
from evennia import utils
from evennia.utils import search

def affect_apply(character, affect_name, duration, character_message, room_message, **kwargs):
    """
    This function applies the spell a character is affected
    by, and creates a delay call for removing it.
    """
    
    if affect_name in character.db.spell_affects:
        character.msg("There was an error in adding %s to your spell affects, as it cannot be listed twice." % affect_name)
        return

    duration = int(duration * settings.TICK_OBJECT_TIMER)
    duration_time = time.time() + duration

    character.db.spell_affects[affect_name] = {"duration": duration_time}
    
    def remove_underscore(string):
        if "_" in string:
            string = string.replace("_", " ")
        return string
    
    # Applies will take the form of ["strength", -2]
    if "apply_1" in kwargs:
        apply_type = remove_underscore(kwargs["apply_1"][0])
        apply_1_type = apply_type
        apply_1_amount = kwargs["apply_1"][1]
        character.db.spell_affects[affect_name][apply_1_type] = apply_1_amount
    if "apply_2" in kwargs:
        apply_type = remove_underscore(kwargs["apply_2"][0])
        apply_2_type = apply_type
        apply_2_amount = kwargs["apply_2"][1]
        character.db.spell_affects[affect_name][apply_2_type] = apply_2_amount
    if "apply_3" in kwargs:
        apply_type = remove_underscore(kwargs["apply_3"][0])
        apply_3_type = apply_type
        apply_3_amount = kwargs["apply_3"][1]
        character.db.spell_affects[affect_name][apply_3_type] = apply_3_amount

    affects_return = utils.delay(duration,
                                 affect_remove, character, affect_name, character_message, room_message,
                                 persistent=True)
    
    if not character.ndb.affects_return:
        character.ndb.affects_return = {}
        character.ndb.affects_return[affect_name] = affects_return   
    else:
        character.ndb.affects_return[affect_name] = affects_return

def affect_remove(character, affect_name, character_message, room_message):
    """
    This function removes the spell a character is affected by
    from their affects dictionary.
    """

    if character.ndb.affects_return:
        if character.ndb.affects_return[affect_name]:
            del character.ndb.affects_return[affect_name]

    # Make sure the affect hasn't been dispelled or similar.
    if character.db.spell_affects[affect_name]:
        del character.db.spell_affects[affect_name]
        if character_message:
            character.msg(character_message)
        if room_message:
            # Deal with invisible objects/characters for output.
            # Assemble a list of all possible lookers.
            lookers = list(cont for cont in character.location.contents if "mobile" in cont.tags.all() or "player" in cont.tags.all())
            for looker in lookers:
                # Exclude the character, who got their output above.
                if looker != character:

                    # Give output to those who can no longer see the character.
                    if not rules.is_visible(character, looker):
                        looker.msg(room_message)
                        
                        
def attributes_cost(character):
    """
    This function determines the experience cost of getting an
    additional attribute (e.g. strength, dexterity, etc.) bonus.
    The formula for this has to be calculated from the next four
    xp steps.
    """
    
    cost = current_experience_step(character, 0)
    cost += current_experience_step(character, 1)
    cost += current_experience_step(character, 2)
    cost += current_experience_step(character, 3)    

    return cost


def auras_objects(looker, object):
    """
    This function takes a character looking at an object, and
    determines what auras will show up before the object's
    description in a room, and will return a string of those
    auras.
    """

    aura_string = ""

    if "invisible" in object.db.extra_flags and looker.get_affect_status("detect invis"):
        aura_string += "(Invis)"
    if "evil" in object.db.extra_flags and looker.alignment > 333 and looker.get_affect_status("detect evil"):
        aura_string += "|r(Red Aura)|R"
    if "magic" in object.db.extra_flags and looker.get_affect_status("detect magic"):
        aura_string += "(Magical)"
    if "glow" in object.db.extra_flags:
        aura_string += "(Glowing)"
    if "hum" in object.db.extra_flags:
        aura_string += "(Humming)"

    if aura_string:
        aura_string += " "
    return aura_string

def auras_characters(looker, character):
    """
    This function takes a character looking at a character,
    and determines what auras will show up before the
    character's description in a room, and will return a
    string of those auras.
    """

    aura_string = ""

    # Handle quest starter notification.
    if "mobile" in character.tags.all():
        if character.attributes.has("quests"):
            if character.db.quests:
                for quest in character.db.quests:
                    if "starter" in character.db.quests[quest]:
                        if looker.attributes.has("quests"):
                            if looker.db.quests:
                                if quest not in looker.db.quests:
                                    # The starter mobile has the level guidepost for the quest
                                    # as the value corresponding to starter.
                                    if character.db.quests[quest]["starter"] - looker.level <= -2:
                                        color = "|g"
                                    elif character.db.quests[quest]["starter"] - looker.level <= 4:
                                        color = "|y"
                                    else:
                                        color = "|r"
                                    aura_string += "%s(!)|Y" % color
                            else:
                                # The starter mobile has the level guidepost for the quest
                                # as the value corresponding to starter.
                                if character.db.quests[quest]["starter"] - looker.level <= -2:
                                    color = "|g"
                                elif character.db.quests[quest]["starter"] - looker.level <= 4:
                                    color = "|y"
                                else:
                                    color = "|r"
                                aura_string += "%s(!)|Y" % color

    # Handle actual auras.
    if character.get_affect_status("invisible") and looker.get_affect_status("detect invis"):
        aura_string += "(Invis)"
    if character.alignment < -333 and looker.alignment > 333 and looker.get_affect_status("detect evil"):
        aura_string += "|R(Red Aura)|Y"
    if character.get_affect_status("faerie fire"):
        aura_string += "|M(Pink Aura)|Y"
    if character.get_affect_status("sanctuary"):
        aura_string += "|W(White Aura)|Y"
    if character.get_affect_status("flaming shield"):
        aura_string += "|R(|rF|Rl|ra|Rm|ri|Rn|rg |RA|ru|Rr|ra|R)|Y"
    if character.get_affect_status("fly"):
        aura_string += "(Flying)"

    if aura_string:
        aura_string += " "
    return aura_string


def calculate_experience(mobile):
    """
    This function calculates the total experience awarded for
    killing a mobile. This experience is later modified in
    actual combat for bonuses dependent upon the attacker
    (racial hatred, alignment).
    """
    level_xp = mobile.db.level * mobile.db.level * mobile.db.level * 5
    hp_xp = mobile.hitpoints_maximum
    ac_xp = (mobile.armor_class - 50) * 2
    damage_xp = ((3 * mobile.db.level / 4) + mobile.damroll) * 50
    hitroll_xp = mobile.hitroll * mobile.db.level * 10

    experience = level_xp + hp_xp - ac_xp + damage_xp + hitroll_xp

    if mobile.get_affect_status("sanctuary"):
        experience *= 1.5

    if mobile.get_affect_status("flameshield"):
        experience *= 1.4

    if mobile.db.eq_slots["wielded, primary"]:
        experience *= 1.25

    if mobile.db.eq_slots["wielded, secondary"]:
        experience *= 1.2

    if mobile.db.special_function:
        if ("breath_any" or "cast_psionicist" or "cast_undead" or
                "breath_gas" or "cast_mage") in mobile.db.special_function:
            experience *= 1.33

        elif ("breath_fire" or "breath_frost" or "breath_acid" or
                "breath_lightning" or "cast_cleric" or "cast_judge" or
                "cast_ghost") in mobile.db.special_function:
            experience *= 1.2

        elif ("poison" or "thief") in mobile.db.special_function:
            experience *= 1.05

        elif "cast_adept" in mobile.db.special_function:
            experience *= 0.5

    # Finally, randomize slightly, and check for a floor of 50.
    experience = int(random.uniform(0.9, 1.1) * experience)
    if experience < 50:
        experience = 50

    return experience

def calculate_gold(mobile):
    """
    This function calculates the total gold carried by a
    mobile.
    """

    gold = int(calculate_experience(mobile) // 3)

    return gold


def can_see(target, looker):
    """
    This function checks to see (heh) if a target is visible to
    a looker, and returns a boolean of True if the looker can
    see the target, and False if not.
    """
    
    if looker.get_affect_status("blind"):
        return False
    elif target.get_affect_status("hide") and not looker.get_affect_status("detect hidden"):
        return False
    elif target.get_affect_status("invisible") and not looker.get_affect_status("detect invis"):
        return False
    else:
        return True

def carry_permitted(object, new_object):
    """
    This function will take an object (mobile, player or container),
    and return a boolean based on whether the new_object can be
    carried/contained, as the case may be.
    """

    carry_weight_maximum = 0

    if "player" in object.tags.all():

        average_attribute = (object.strength + object.constitution) / 2

        if object.level > 65:
            carry_weight_maximum = (strength_carry(average_attribute) + (object.level * object.strength) / 8)
        else:
            carry_weight_maximum = strength_carry(average_attribute)

    elif "mobile" in object.tags.all():
        carry_weight_maximum = 9999999

    elif "object" in object.tags.all():
        if object.db.item_type == "container":
            carry_weight_maximum = object.db.weight_maximum

    current_contents_weight = weight_contents(object)

    if new_object.weight:
        if current_contents_weight + new_object.weight > carry_weight_maximum:
            return "weight_fail"

    if "player" in object.tags.all() or "mobile" in object.tags.all():
        carry_number_maximum = int(object.level / 4) + 2 + int((object.strength + object.dexterity + object.constitution) / 3)

        total_equipped = 0

        for obj in object.contents:
            if obj.db.equipped:
                total_equipped += 1

        current_contents_number = len(object.contents) - total_equipped

        if current_contents_number + 1 > carry_number_maximum:
            return "number_fail"

    return True


def check_ready_to_level(character):
    """
    This function checks if a character has grown sufficiently
    to level up. Characters may level, at fastest, on every
    sixth train. Attribute gains count as four.
    """
    
    step = (character.level +
            character.db.hitpoints["trains spent"] +
            character.db.mana["trains spent"] +
            character.db.moves["trains spent"] +
            (character.db.attribute_trains["strength"] * 4) +
            (character.db.attribute_trains["intelligence"] * 4) +
            (character.db.attribute_trains["wisdom"] * 4) +
            (character.db.attribute_trains["dexterity"] * 4) +
            (character.db.attribute_trains["constitution"] * 4) +
            int(character.db.practices_spent))
    
    if step >= ((character.level - 1) * 6) + 5:
        return True
    else:
        return False

def check_return_visible(character):
    """
    This function is designed to be used with offensive spells
    or attacks to determine whether the character is hidden or
    invisible, and, if so, cancel that state and give appropriate
    output to the character's room that they are returning to
    visibility.
    """
    
    if character.get_affect_status("hide"):
        affect_remove(character,
                        "hide",
                        "You are no longer hidden.",
                        "%s emerges from the shadows." % (character.key[0].upper() + character.key[1:])
                        )

    if character.get_affect_status("invisible"):
        affect_remove(character,
                        "invisible",
                        "You are no longer invisible.",
                        "A roughly-humanoid shape shimmers and %s becomes visible." % (character.key[0].upper() + character.key[1:])
                        )

def classes_current(character, **kwargs):
    """
    This function will eventually evaluate all the skills that
    a character has learned and compare them to the character's
    level to determine what their most-used class (or classes,
    at higher levels) is. For now just returns default.
    """
    
    # As the sort is done below, the below order is also the
    # tiebreaker order.
    colleges = {"warrior": 0,
                "thief": 0,
                "druid": 0,
                "ranger": 0,
                "paladin": 0,
                "mage": 0,
                "bard": 0,
                "cleric": 0,
                "psionicist": 0
                }
    
    # Each college has more or less skills in it than others, from
    # the most (psionicist) to least (druid/warrior/thief). We
    # apply a weighting factor to each skill learned in each college
    # to make up for this. Eventually, this should be calculated,
    # rather than magic numbers.
    factor = {"psionicist": 1.00,
              "cleric": 1.070,
              "druid": 1.314,
              "bard": 1.394,
              "mage": 1.394,
              "paladin": 1.438,
              "ranger": 1.438,
              "thief": 1.643,
              "warrior": 1.917
              }
    
    if not character.db.skills:
        return["default"]
    
    # Run through skills known to character.
    for skill in character.db.skills:
        
        # Grab the skill dictionary for each skill.
        skill_dict = rules_skills.get_skill(skill_name=skill)
        
        # Run through the classes eligible to learn each skill.
        for college in skill_dict["classes"]:
            
            # If their level equals or exceeds the level to learn
            # the skill in that college, they get credit for work
            # in that college.
            if skill_dict["classes"][college] <= character.level:
                colleges[college] += factor[college]
    
    # Sorting the colleges based on weighted skills in each.
    
    # Make a copy to operate on.
    sortable_colleges = colleges.copy()
    ordered_list = []
    number_results = int(character.level / 20 + 1)
    rank = 1
    total = len(sortable_colleges)

    while rank <= total:
        
        # Find the highest value still in the list, and append to
        # the ordered list.
        ordered_list.append(max(sortable_colleges, key=sortable_colleges.get))
        
        # Delete that value from the colleges copy.
        del sortable_colleges[ordered_list[rank-1]]
        rank += 1

    if "all" in kwargs:
        output_list = []
        for output_college in ordered_list:
            if colleges[output_college] > 0:
                output_list.append(output_college)

        return output_list
    else:
        if number_results > 1:

            # Check to make sure that you aren't returning colleges with
            # no skills in them.
            for index in range(0, total):
                if colleges[ordered_list[index]] == 0 or index == number_results + 1:
                    break

            return ordered_list[0:index - 1]
        else:
            return ordered_list[0]

def constitution_hitpoint_bonus(character):
    """
    This function returns the amount of bonus hitpoints that a
    character receives on gaining another set of hitpoints.
    """
    con = character.constitution
    
    if con == 0:
        return -4
    elif con == 1:
        return -3
    elif con < 4:
        return -2
    elif con < 7:
        return -1
    elif con < 15:
        return 0
    elif con < 16:
        return 1
    elif con < 18:
        return 2
    elif con < 20:
        return 3
    elif con < 22:
        return 4
    elif con < 23:
        return 5
    elif con < 24:
        return 6
    elif con < 25:
        return 7
    else:
        return 8 
    
    
def current_experience_step(character, extra_step):
    """
    This function uses a character's current total trains and
    practices spent to determine the experience step that the
    character is currently at.
    """

    step = (character.level +
            character.db.hitpoints["trains spent"] +
            character.db.mana["trains spent"] +
            character.db.moves["trains spent"] +
            (character.db.attribute_trains["strength"] * 4) +
            (character.db.attribute_trains["intelligence"] * 4) +
            (character.db.attribute_trains["wisdom"] * 4) +
            (character.db.attribute_trains["dexterity"] * 4) +
            (character.db.attribute_trains["constitution"] * 4) +
            int(character.db.practices_spent) +
            extra_step)
    
    experience_cost = int(((1 + (step/8.303)) ** 3) * 176.889)
    
    return experience_cost

def do_damage_noncombat(victim, victim_source, looker_source, damage, damage_type):
    """
    This function is used to do damage outside of combat.
    """
    
        try:
            victim.take_damage(damage)
        except Exception:
            logger.log_trace("Error in damaging character in do_damage_noncombat.")

        # Get the victim started healing, if not already.
        try:
            if not victim.attributes.has("heal_ticker"):
                timestamp = victim.key + str(time.time())
                tickerhandler.add(30, victim.at_update, timestamp)
                victim.db.heal_ticker = timestamp
            elif not victim.db.heal_ticker:
                timestamp = victim.key + str(time.time())
                tickerhandler.add(30, victim.at_update, timestamp)
                victim.db.heal_ticker = timestamp
        except Exception:
            logger.log_trace("Error in checking if healing needed in do_damage_noncombat.")

        # Give output.
        try:
            if source == victim:
                source_name = "Your"
            else:
            
            victim.msg("%s %s %s you."
                           % (victim_source,
                              damage_type,
                              rules_combat.get_damagestring("victim", damage)                              
                              )
                           )
            
            # Deal with invisible characters for output.
            # Assemble a list of all possible lookers.
            lookers = list(cont for cont in victim.location.contents if "mobile" in cont.tags.all() or "player" in cont.tags.all())
            for looker in lookers:
                # Exclude the victim, who got their output above.
                if looker != victim:
                    if is_visible(victim, looker):
                        looker.msg("%s %s %s %s."
                                             % ((looker_source[0].upper() + looker_source[1:]),
                                                damage_type,
                                                rules_combat.get_damagestring("victim", damage),
                                                victim.key
                                                )
                                             )
        except Exception:
            logger.log_trace("Error in giving output in do_damage_noncombat.")

        # Check at the end of processing damage to see if the victim is dead.
        if victim.hitpoints_current <= 0:
            do_death_noncombat(victim, victim_source, looker_source, damage_type)

def do_death_noncombat(victim, victim_source, looker_source, damage_type):
    """
    This handles non-cobmat death and returns some output. For now,
    only handles player death.
    """

    # Give death output.
    try:
        victim.msg("You have been |rKILLED|n!!!\n You awaken again at your "
                   "home location.")

        # Deal with invisible characters for output.
        # Assemble a list of all possible lookers.
        lookers = list(cont for cont in victim.location.contents if "mobile" in cont.tags.all() or "player" in cont.tags.all())
        for looker in lookers:
            # Exclude the victim, who got their output above.
            if looker != victim:
                if is_visible(victim, looker):
                    looker.msg("%s %s has KILLED %s!!!"
                                            % (looker_source[0].upper() + looker_source[1:]),
                                               damage_type,
                                               victim.key
                                               )
                                         )
    except Exception:
        logger.log_trace("Error in giving output of death in do_death_noncombat.")

    # Handle player death.

    # Step 1 Make a corpse.
    corpse = False

    # 1(a) Check at none to see if there is an existing corpse.
    try:
        object_candidates = search.search_tag("pc corpse")

        for object in object_candidates:
            if not object.location:
                corpse = object
                corpse.key = "the corpse of %s" % victim.key
                break

    except Exception:
        logger.log_trace("Error in finding player corpse in do_death_noncombat.")

    # 1(b) If not a ready corpse, make one.
    try:
        if not corpse:
            # Create corpse.
            corpse = create_object("objects.PC_Corpse", key=("the corpse of %s"
                                                             % victim.key))
    except Exception:
        logger.log_trace("Error in creating player corpse in do_death_noncombat.")

    corpse.db.desc = ("The corpse of %s lies here." % victim.key)
    corpse.location = victim.location

    try:
        rules.set_disintegrate_timer(corpse)
    except Exception:
        logger.log_trace("Error setting disintegrage timer for player corpse in do_death_noncombat.")

    # Step 2 Increment hero deaths.
    victim.db.died += 1

    # Heroes keep their items.

    # Step 3 Cleanup the hero.
    try:
        # 3(a) Clear wait state.
        if victim.ndb.wait_state:
            wait_state_remove(victim)

        # 3(b) Clear spell affects and return calls.
        if victim.db.spell_affects:
            for affect_name in victim.db.spell_affects:
                affect_remove(victim, affect_name, "", "")

    except Exception:
        logger.log_trace("Error in cleaning up player in do_death_noncombat.")

    # Step 4 Do xp penalty, if above level 5.
    try:
        if victim.level > 5:
            experience_loss = int(settings.EXPERIENCE_LOSS_DEATH * rules.experience_loss_base(victim))
            victim.db.experience_total -= experience_loss

            victim.msg("You lose %s experience as a result of your death!" % experience_loss)

    except Exception:
        logger.log_trace("Error in finding player corpse in do_death_noncombat.")

        # Do gold penalty, after figuring out how much it should be.

    # Step 5 Reset dead players to one hitpoint, and move to home.
    try:
        victim.hitpoints_damaged = victim.hitpoints_maximum - 1
        victim.move_to(victim.home, quiet=True)

        victim.location.msg_contents("A beaten and bedraggled %s rises from the dead."
                                     % victim.key,
                                     exclude=victim)
    except Exception:
        logger.log_trace("Error in resetting player ot one hp and moving home in do_death_noncombat.")

    send_prompt(victim)
          

def experience_loss_base(character):
    """
    This function calculates the experience that fleeing, death,
    and the like use to calculate proportional loss from.
    """
    
    loss = (current_experience_step(character, -1) +
            current_experience_step(character, -2) +
            current_experience_step(character, -3) +
            current_experience_step(character, -4) +
            current_experience_step(character, -5)
            )
    
    return loss


def fuzz_number(number):
    """
    This function simply adds slight variation to a number.
    """

    random_number = random.randint(1, 4)
    if random_number < 2:
        return number - 1
    elif random_number > 3:
        return number + 1
    else:
        return number


def gain_experience(mobile, hp_gain):
    """
    This function calculates the amount of experience that
    needs to be regained by a mobile to accommodate its
    hit point gain.
    """

    if hp_gain > 0:
        percent_hp_recovered = hp_gain / mobile.db.hitpoints["damaged"]
        experience_awarded = math.ceil(mobile.db.experience_total -
                                       mobile.db.experience_current)

        experience_gain = int(percent_hp_recovered * experience_awarded)
    else:
        experience_gain = 0

    return experience_gain


def gain_hitpoints(character):
    """
    This method calculates the amount of passive hitpoint gain,
    and returns that number.
    """

    if "mobile" in character.tags.all():
        hp_gain = character.db.level * 3 / 2
    else:
        if character.db.level < 5:
            hp_gain = character.db.level

        else:
            hp_gain = 5

        if character.db.position == "sleeping":
            hp_gain += character.constitution * 2
        elif character.db.position == "resting":
            hp_gain += character.constitution

        # Hitpoint gain is impacted by thirst and hunger. If you are full,
        # you get a bonus to gain. If you are starving and parched, you
        # get no benefit. Sliding scale between.

        hunger_modifier = character.db.hunger/16000
        thirst_modifier = character.db.thirst/16000
        total_food_modifier = 1 + hunger_modifier + thirst_modifier

        hp_gain *= total_food_modifier

        # Need to accommodate furniture, poisoning, and
        # enhanced healing in here once coded.

    if "heal modifier" in rules_race.get_race(character.race):
        hp_gain += rules_race.get_race(character.race)["heal modifier"]

    hp_gain = math.ceil(hp_gain)

    if hp_gain > character.db.hitpoints["damaged"]:
        return character.db.hitpoints["damaged"]
    else:
        return hp_gain


def gain_mana(character):
    """
    This method calculates the amount of passive mana gain,
    and returns that number.
    """

    if "mobile" in character.tags.all():
        mana_gain = character.db.level

    else:
        if character.db.level < 5:
            mana_gain = math.ceil(character.db.level / 2)
        else:
            mana_gain = 5

        if character.db.position == "sleeping":
            mana_gain += character.intelligence * 2
        elif character.db.position == "resting":
            mana_gain += character.intelligence

        # Mana gain is impacted by thirst and hunger. If you are full,
        # you get a bonus to gain. If you are starving and parched, you
        # get no benefit. Sliding scale between.

        hunger_modifier = character.db.hunger/16000
        thirst_modifier = character.db.thirst/16000
        total_food_modifier = 1 + hunger_modifier + thirst_modifier

        mana_gain *= total_food_modifier

        # If drunk, you get a further bonus
        if character.db.drunk > 0:
            mana_gain *= 2

        # Need to accommodate furniture, poisoning, and
        # enhanced healing in here once coded.

    if "mana modifier" in rules_race.get_race(character.race):
        mana_gain += character.db.level * \
            rules_race.get_race(character.race)["mana modifier"]

    mana_gain = math.ceil(mana_gain)

    if mana_gain > character.db.mana["spent"]:
        return character.db.mana["spent"]
    else:
        return mana_gain


def gain_moves(character):
    """
    This method calculates the amount of passive moves gain,
    and returns that number.
    """

    if "mobile" in character.tags.all():
        moves_gain = character.db.level

    else:
        if (character.db.level * 2) > 15:
            moves_gain = character.db.level * 2
        else:
            moves_gain = 15

        if character.db.position == "sleeping":
            moves_gain += character.dexterity * 2
        elif character.db.position == "resting":
            moves_gain += character.dexterity

        # Mana gain is impacted by thirst and hunger. If you are full,
        # you get a bonus to gain. If you are starving and parched, you
        # get no benefit. Sliding scale between.

        hunger_modifier = character.db.hunger/16000
        thirst_modifier = character.db.thirst/16000
        total_food_modifier = 1 + hunger_modifier + thirst_modifier

        moves_gain *= total_food_modifier

        # Need to accommodate furniture, poisoning, and
        # enhanced healing in here once coded.

    if "moves modifier" in rules_race.get_race(character.race):
        moves_gain += character.db.level * \
            rules_race.get_race(character.race)["moves modifier"]

    moves_gain = math.ceil(moves_gain)

    if moves_gain > character.db.moves["spent"]:
        return character.db.moves["spent"]
    else:
        return moves_gain


def get_area_info(area_name):
    """
    This function takes either a) an area name and returns the
    formatted name of the area, and the levels it is for in
    parentheses, or b) "all", and returns a list of all
    unformatted area names.
    """

    area_dictionary = {
        "crystalmir lake": {
            "formatted name": "Crystalmir Lake",
            "level range": "[  1 -  10]",
            "repop message": "The wind blows through the fields and across the lake."
        },
        "dangerous neighborhood": {
            "formatted name": "Dangerous Neighborhood",
            "level range": "[  5 -  15]",
            "repop message": "Still more hoodlums emerge from the wasted landscape."
        },
        "dragon cult": {
            "formatted name": "Dragon Cult",
            "level range": "[  5 -  15]",
            "repop message": "A too-smiling man says 'Do you know of the dragon rapture?'"
        },
        "dwarven daycare": {
            "formatted name": "Dwarven Daycare",
            "level range": "[  1 -  10]",
            "repop message": "Small children run everywhere, as teachers sigh."
        },
        "edens grove": {
            "formatted name": "Eden's Grove",
            "level range": "[   All   ]",
            "repop message": "All returns to normal in Eden's Grove."
        },
        "elemental canyon": {
            "formatted name": "Elemental Canyon",
            "level range": "[  5 -  15]",
            "repop message": "The many elements combine to restore the canyon."
        },
        "faerie ring": {
            "formatted name": "Faerie Ring",
            "level range": "[ 10 -  15]",
            "repop message": "What's that, flitting through the mushrooms???"
        },
        "fire newts": {
            "formatted name": "Land of the Fire Newts",
            "level range": "[  5 -  15]",
            "repop message": "Small gouts of fire spew out from the very rock."
        },
        "gnome village": {
            "formatted name": "Gnome Village",
            "level range": "[  5 -  15]",
            "repop message": "The happy sounds of gnomish life surround you."
        },
        "graveyard": {
            "formatted name": "Graveyard",
            "level range": "[  5 -  10]",
            "repop message": "A cold breeze groans its way through the graves."
        },
        "haon dor": {
            "formatted name": "Haon Dor",
            "level range": "[  5 -  10]",
            "repop message": "The trees creak, and you see eyes peering out of the darkness."
        },
        "holy grove": {
            "formatted name": "Holy Grove",
            "level range": "[  5 -  15]",
            "repop message": "The tranquillity of the grove is broken by slight sounds of activity."
        },
        "miden'nir": {
            "formatted name": "Miden'nir",
            "level range": "[  5 -  15]",
            "repop message": "The sounds of rampant goblin savagery filter through the forest."
        },
        "smurf village": {
            "formatted name": "Smurf Village",
            "level range": "[  1 -  10]",
            "repop message": "La, la, lalalala, la, la, lala, LA!!!!!!!"
        },
        "the library": {
            "formatted name": "The Library",
            "level range": "[  1 -  10]",
            "repop message": "The sounds of unusual activity echo through the stacks."
        },
        "the rats' lair": {
            "formatted name": "The Rats' Lair",
            "level range": "[  1 -  10]",
            "repop message": "The sound of maddened scrabbling echoes through the walls."
        },
        "training tower": {
            "formatted name": "Training Tower",
            "level range": "[  1 -   5]",
            "repop message": "The sounds of learning and active training fill the tower."
        },
        "troll den": {
            "formatted name": "Troll Den",
            "level range": "[  10 -  15]",
            "repop message": "Roaring and, is that cracking, fill the air."
        },
        "the circus": {
            "formatted name": "The Circus",
            "level range": "[   1 -  10]",
            "repop message": "Clowns, clowns, and still more clowns caper by."
        }
    }

    if area_name == "all":
        return area_dictionary
    
    if area_name in area_dictionary:
        return "%s %s" % (area_dictionary[area_name]["formatted name"], area_dictionary[area_name]["level range"])
    else:
        return "Unknown [  Unknown ]"

def get_area_name(object):
    """
    This function determines the area that an object (room, mobile, exit,
    object) is associated with.
    """
    
    tag = object.tags.all(return_key_and_category=True)
    total_tags = len(tag)

    for index in range(0, total_tags):
        if tag[index][1] == "area name":
            area = tag[index][0]
    
    return area

def get_visual_output(object, looker, **kwargs):
    """
    This function will take an object and a character looking at
    that object, and return the appropriate output for that object-
    looker pair. Output will have to be capitalized, as appropriate,
    on the back-end.
    
    Supports the following kwargs:
    possessive=True - if a mobile or player is the object, will return
                      the correct possessive pronoun output.
    reflexive=True - if a mobile or player is the object, will return
                      the correct possessive pronoun output.
    """
    
    if "mobile" in object.tags.all() or "player" in object.tags.all():
        if "possessive" in kwargs:
            if kwargs["possessive"]:
                if is_visible(object, looker):
                    return pronoun_possessive(object)
                else:
                    return "their"
                
        if "reflexive" in kwargs:
            if kwargs["reflexive"]:
                if is_visible(object, looker):
                    return pronoun_reflexive(object)
                else:
                    return "themselves"        
        
        if is_visible(object, looker):
            return object.key
        else:
            return "someone"
    
    if "object" in object.tags.all():
        if is_visible(object, looker):
            return object.key
        else:
            return "something"
        

def hitpoints_cost(character):
    """
    This function determines the experience cost of getting an
    additional amount of hitpoints.
    """
    return current_experience_step(character, 0)


def intelligence_learn_rating(character):
    """
    This function returns the learn rating of a character
    based on their intelligence.
    """
    int = character.intelligence
    
    if int == 0:
        return 3
    elif int == 1:
        return 5
    elif int == 2:
        return 7
    elif int == 3:
        return 8
    elif int == 4:
        return 9
    elif int == 5:
        return 10
    elif int == 6:
        return 11
    elif int == 7:
        return 12
    elif int == 8:
        return 13
    elif int == 9:
        return 15
    elif int == 10:
        return 17
    elif int == 11:
        return 19
    elif int == 12:
        return 22
    elif int == 13:
        return 25
    elif int == 14:
        return 28
    elif int == 15:
        return 31
    elif int == 16:
        return 34
    elif int == 17:
        return 37
    elif int == 18:
        return 40
    elif int == 19:
        return 44
    elif int == 20:
        return 49
    elif int == 21:
        return 55
    elif int == 22:
        return 60
    elif int == 23:
        return 70
    elif int == 24:
        return 85
    else:
        return 90

def intelligence_mana_bonus(character):
    """
    This function returns the amount of bonus mana that a
    character receives on gaining another set of mana based
    on intelligence.
    """
    int = character.intelligence
    
    if int < 16:
        return 0
    elif int < 20:
        return 1
    elif int < 22:
        return 2
    elif int < 24:
        return 3
    elif int < 25:
        return 4
    else:
        return 5

def is_visible_character(target, looker):
    """
    DO NOT USE ANY LONGER. HERE FOR BACKWARD COMPATIBILITY.
    """
    if looker.get_affect_status("blind"):
        return False
    if target.get_affect_status("hide") and not looker.get_affect_status("detect hidden"):
        return False
    if target.get_affect_status("invisible") and not looker.get_affect_status("detect invis"):
        return False
    if "act_flags" in target.db.all:
        if "total invis" in target.db.act_flags:
            return False
    
    return True
    
def is_visible(target, looker, **kwargs):
    """
    This function returns a boolean as to whether one character/object
    is visible to another currently.
    
    Kwargs:
    arrive = True - If arrive is flagged as true, the function will let
    you know whether someone's arrival in the room is visible (sneak vs.
    hide).    
    """
    
    # Dealing with arrival visibility.
    if "arrive" in kwargs:
        if looker.get_affect_status("blind"):
            return False
        if target.get_affect_status("sneak") and not looker.get_affect_status("detect hidden"):
            return False
        if target.get_affect_status("invisible") and not looker.get_affect_status("detect invis"):
            return False        
        
        return True

    # Dealing with character visibility.
    if "mobile" in target.tags.all() or "player" in target.tags.all():
        if looker.get_affect_status("blind"):
            return False
        if target.get_affect_status("hide") and not looker.get_affect_status("detect hidden"):
            return False
        if target.get_affect_status("invisible") and not looker.get_affect_status("detect invis"):
            return False
        if "mobile" in target.tags.all():
            if target.db.act_flags:
                if "total invis" in target.db.act_flags:
                    return False

    # Dealing with object visibility.
    else:
        if looker.get_affect_status("blind"):
            return False
        if target.db.extra_flags:
            if "invisible" in target.db.extra_flags and not looker.get_affect_status("detect invis"):
                return False
            
    return True

def level_cost(character):
    """
    This function determines the experience cost of increasing a
    character one level.
    """
    
    return current_experience_step(character, 0)


def make_object(location, equipped, reset_object):
    new_object = ""

    # First, search for all objects of that type and pull out
    # any that are at "None".
    object_candidates = search.search_object(reset_object)

    for object in object_candidates:
        if not object.location:
            new_object = object

    # If it is not in "None", find the existing object in the world
    # and copy it.
    if not new_object:

        object_to_copy = object_candidates[0]
        new_object = object_to_copy.copy()
        new_object.key = object_to_copy.key
        new_object.alias = object_to_copy.aliases
        if new_object.db.equipped:
            new_object.db.equipped = False
        new_object.home = location

    # Either way, put it where it should be.
    new_object.location = location

    # Clear any enchantment/poison/other affects.
    new_object.db.spell_affects = {}

    # Set level, other values, and/or fuzz numbers as necessary
    new_object.db.level = 1
    if new_object.db.item_type == "armor":
        new_object.db.armor = set_armor(new_object.db.level)
    elif new_object.db.item_type == "weapon":
        new_object.db.damage_low, new_object.db.damage_high = set_weapon_low_high(new_object.db.level)
    elif new_object.db.item_type == "scroll":
        new_object.db.spell_level = fuzz_number(new_object.db.spell_level_base)
    elif new_object.db.item_type == "wand" or new_object.db.item_type == "staff":
        new_object.db.spell_level = fuzz_number(new_object.db.spell_level_base)
        new_object.db.charges_maximum = fuzz_number(new_object.db.charges_maximum_base)
        new_object.db.charges_current = new_object.db.charges_maximum
    elif new_object.db.item_type == "potion" or new_object.db.item_type == "pill":
        new_object.db.spell_level = fuzz_number(fuzz_number(new_object.db.spell_level_base))

    # If it should be equipped, equip it.
    if equipped:
        if not new_object.db.equipped:
            if new_object.db.item_type == "weapon":
                new_object.wield_to(location)
            else:
                new_object.wear_to(location)

    return new_object


def mana_cost(character):
    """
    This function determines the experience cost of getting an
    additional amount of mana.
    """
    return current_experience_step(character, 0)


def moves_cost(character):
    """
    This function determines the experience cost of getting an
    additional amount of moves.
    """
    return current_experience_step(character, 0)

def player_in_area(area_name):
    """
    This function checks whether there is a player in an area
    or not.
    """
    players = search.search_tag("player")
    
    if players:
        for player in players:
            if player.location:
                if area_name in player.location.tags.all():
                    return True
    
    return False
    
def pronoun_object(character):
    """
    This function determines the correct object pronoun for a
    character.
    """

    if character.sex == "male":
        return "him"
    elif character.sex == "female":
        return "her"
    else:
        return "them"

def pronoun_possessive(character):
    """
    This function determines the correct possessive pronoun for a
    character.
    """

    if character.sex == "male":
        return "his"
    elif character.sex == "female":
        return "her"
    else:
        return "their"

def pronoun_reflexive(character):
    """
    This function determines the correct reflexive pronoun for a
    character.
    """

    if character.sex == "male":
        return "himself"
    elif character.sex == "female":
        return "herself"
    else:
        return "themselves"

def pronoun_subject(character):
    """
    This function determines the correct subject pronoun for a
    character.
    """

    if character.sex == "male":
        return "he"
    elif character.sex == "female":
        return "she"
    else:
        return "they"


def remove_disintegrate_timer(obj):
    """
    This function removes the timer that comes from dropping an
    object.
    """

    if "pc corpse" in obj.tags.all():
        tickerhandler.remove(settings.PC_CORPSE_DISINTEGRATE_TIME, obj.at_disintegrate, obj.db.disintegrate_ticker)
        obj.db.disintegrate_ticker = ""
        obj.tags.remove("disintegrating")
    else:
        tickerhandler.remove(settings.DEFAULT_DISINTEGRATE_TIME, obj.at_disintegrate, obj.db.disintegrate_ticker)
        obj.db.disintegrate_ticker = ""
        obj.tags.remove("disintegrating")


def send_prompt(character):
    """
    This function builds and then sends a prompt to the
    character.
    """

    if "wait_state" not in character.ndb.all:
        prompt_wait = "|gReady!|n"
    elif character.ndb.wait_state >= 12:
        prompt_wait = "|rCompleting action!"
    elif character.ndb.wait_state > 0:
        prompt_wait = "|yRecovering.|n"
    else:
        prompt_wait = "|gReady!|n"
    prompt = "<|r%d|n/|R%d hp |b%d|n/|B%d mana |y%d|n/|Y%d moves|n %s>\n" % (
        character.hitpoints_current,
        character.hitpoints_maximum,
        character.mana_current,
        character.mana_maximum,
        character.moves_current,
        character.moves_maximum,
        prompt_wait)
    character.msg(prompt=prompt)


def set_armor(level):
    """
    This function sets the armor value of a piece of armor.
    """

    return round(fuzz_number((level/4) + 2))


def set_disintegrate_timer(obj):
    """
    This function sets the timer that comes from dropping an
    object.
    """

    if "pc corpse" in obj.tags.all():
        timestamp = obj.key + str(time.time())
        tickerhandler.add(settings.PC_CORPSE_DISINTEGRATE_TIME, obj.at_disintegrate, timestamp)
        obj.db.disintegrate_ticker = timestamp
        obj.tags.add("disintegrating")
    else:
        timestamp = obj.key + str(time.time())
        tickerhandler.add(settings.DEFAULT_DISINTEGRATE_TIME, obj.at_disintegrate, timestamp)
        obj.db.disintegrate_ticker = timestamp
        obj.tags.add("disintegrating")


def set_weapon_low_high(level):
    """
    This function sets the damage range of a weapon.
    """

    low = round(fuzz_number(fuzz_number(level/4 + 2)))
    high = round(fuzz_number(fuzz_number(3*level/4 + 6)))
    return low, high


def strength_carry(rating):
    """
    This function takes a rating and returns the amount of
    weight that can be carried as a result of that rating.
    Differs from other attribute functions because at least
    one use of this function uses an average of strength and
    constitution.
    """

    if rating == 0:
        return 0
    elif rating < 3:
        return 3
    elif rating < 4:
        return 10
    elif rating < 5:
        return 25
    elif rating < 6:
        return 55
    elif rating < 7:
        return 80
    elif rating < 8:
        return 90
    elif rating < 10:
        return 100
    elif rating < 12:
        return 115
    elif rating < 14:
        return 140
    elif rating < 16:
        return 170
    elif rating < 17:
        return 195
    elif rating < 18:
        return 220
    elif rating < 19:
        return 250
    elif rating < 20:
        return 400
    elif rating < 21:
        return 500
    elif rating < 22:
        return 600
    elif rating < 23:
        return 700
    elif rating < 24:
        return 800
    elif rating < 25:
        return 900
    else:
        return 1000

def wait_state_apply(character, wait_state):
    """
    This function takes a character and applies an ndb attribute
    of wait_state, which is a Unix-type time that can be used
    to determine how much longer the wait state will last, if
    needed. The function also creates a delay to call the
    function to eliminate the wait state once it has run.
    """

    wait_state = wait_state / settings.PULSES_PER_SECOND

    if character.ndb.wait_state:
        wait_state = character.ndb.wait_state - time.time() + wait_state
        del character.ndb.wait_state_return

    wait_state_time = time.time() + wait_state

    character.ndb.wait_state = wait_state_time

    wait_state_return = utils.delay(wait_state,
                                    wait_state_remove,
                                    character,
                                    persistent=True)

    character.ndb.wait_state_return = wait_state_return

def wait_state_remove(character):
    """
    This gets called to remove the wait state after it has run.
    """
    if character.ndb.wait_state_return:
        del character.ndb.wait_state_return

    character.ndb.wait_state = 0
    prompt_wait = "|gReady!|n"
    prompt = "<|r%d|n/|R%d hp |b%d|n/|B%d mana |y%d|n/|Y%d moves|n %s>\n" % (character.hitpoints_current,
                                                                             character.hitpoints_maximum,
                                                                             character.mana_current,
                                                                             character.mana_maximum,
                                                                             character.moves_current,
                                                                             character.moves_maximum,
                                                                             prompt_wait)
    character.msg(prompt=prompt)


def weight_contents(object):
    """
    This function will take an object (player, mobile or
    container), and report back the total weight it is
    currently carrying. Checks the weight in the containers
    on the player/mobile.
    """

    weight = 0

    if object.contents:
        for obj in object.contents:
            if obj.weight:
                weight += obj.weight
            if obj.contents:
                for contained_object in obj.contents:
                    if contained_object.weight:
                        weight += contained_object.weight

    return weight


def wisdom_mana_bonus(character):
    """
    This function returns the amount of bonus mana that a
    character receives on gaining another set of mana based
    on wisdom.
    """
    wis = character.wisdom
    
    if wis < 10:
        return 0
    elif wis < 22:
        return 1
    elif wis < 23:
        return 2
    elif wis < 24:
        return 3
    elif wis < 25:
        return 4
    else:
        return 5
        
def wisdom_practices(character):
    """
    This function returns the amount of practice sessions
    that a character receives per experience step based
    on wisdom.
    """
    wis = character.wisdom
    
    if wis < 5:
        return 0
    elif wis < 9:
        return 1
    elif wis < 15:
        return 2
    elif wis < 17:
        return 3
    elif wis < 19:
        return 4
    elif wis < 21:
        return 5
    elif wis < 22:
        return 6
    elif wis < 25:
        return 7
    else:
        return 8
        
