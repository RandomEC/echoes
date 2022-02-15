"""
Commands

Commands describe the input the account can do to the game.

"""

import re
from evennia.commands.command import Command as BaseCommand
from evennia.utils import evtable
from evennia.commands.default.building import ObjManipCommand
from evennia.utils import utils

# Below is here for CmdCharCreate
import time
from codecs import lookup as codecs_lookup
from django.conf import settings
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import utils, create, logger, search
_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS

# from evennia import default_cmds


class Command(BaseCommand):
    """
    Inherit from this if you want to create your own command styles
    from scratch.  Note that Evennia's default commands inherits from
    MuxCommand instead.

    Note that the class's `__doc__` string (this text) is
    used by Evennia to create the automatic help entry for
    the command, so make sure to document consistently here.

    Each Command implements the following methods, called
    in this order (only func() is actually required):
        - at_pre_cmd(): If this returns anything truthy, execution is aborted.
        - parse(): Should perform any extra parsing needed on self.args
            and store the result on self.
        - func(): Performs the actual work.
        - at_post_cmd(): Extra actions, often things done after
            every command, like prompts.

    """

    pass


# -------------------------------------------------------------
#
# The default commands inherit from
#
#   evennia.commands.default.muxcommand.MuxCommand.
#
# If you want to make sweeping changes to default commands you can
# uncomment this copy of the MuxCommand parent and add
#
#   COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"
#
# to your settings file. Be warned that the default commands expect
# the functionality implemented in the parse() method, so be
# careful with what you change.
#
# -------------------------------------------------------------

class MuxCommand(Command):
    """
    This sets up the basis for a MUX command. The idea
    is that most other Mux-related commands should just
    inherit from this and don't have to implement much
    parsing of their own unless they do something particularly
    advanced.

    Note that the class's __doc__ string (this text) is
    used by Evennia to create the automatic help entry for
    the command, so make sure to document consistently here.
    """

    def has_perm(self, srcobj):
        """
        This is called by the cmdhandler to determine
        if srcobj is allowed to execute this command.
        We just show it here for completeness - we
        are satisfied using the default check in Command.
        """
        return super().has_perm(srcobj)

    def at_pre_cmd(self):
        """
        This hook is called before self.parse() on all commands
        """
        pass

    def at_post_cmd(self):
        """
        This hook is called after the command has finished executing
        (after self.func()).
        """
        pass

    def parse(self):
        """
        This method is called by the cmdhandler once the command name
        has been identified. It creates a new set of member variables
        that can be later accessed from self.func() (see below)

        The following variables are available for our use when entering this
        method (from the command definition, and assigned on the fly by the
        cmdhandler):
           self.key - the name of this command ('look')
           self.aliases - the aliases of this cmd ('l')
           self.permissions - permission string for this command
           self.help_category - overall category of command

           self.caller - the object calling this command
           self.cmdstring - the actual command name used to call this
                            (this allows you to know which alias was used,
                             for example)
           self.args - the raw input; everything following self.cmdstring.
           self.cmdset - the cmdset from which this command was picked. Not
                         often used (useful for commands like 'help' or to
                         list all available commands etc)
           self.obj - the object on which this command was defined. It is often
                         the same as self.caller.

        A MUX command has the following possible syntax:

          name[ with several words][/switch[/switch..]] arg1[,arg2,...] [[=|,]
              arg[,..]]

        The 'name[ with several words]' part is already dealt with by the
        cmdhandler at this point, and stored in self.cmdname (we don't use
        it here). The rest of the command is stored in self.args, which can
        start with the switch indicator /.

        This parser breaks self.args into its constituents and stores them in
        the following variables:
          self.switches = [list of /switches (without the /)]
          self.raw = This is the raw argument input, including switches
          self.args = This is re-defined to be everything *except* the switches
          self.lhs = Everything to the left of = (lhs:'left-hand side'). If
                     no = is found, this is identical to self.args.
          self.rhs: Everything to the right of = (rhs:'right-hand side').
                    If no '=' is found, this is None.
          self.lhslist - [self.lhs split into a list by comma]
          self.rhslist - [list of self.rhs split into a list by comma]
          self.arglist = [list of space-separated args (stripped, including '='
              if it exists)]

          All args and list members are stripped of excess whitespace around
          the strings, but case is preserved.
        """
        raw = self.args
        args = raw.strip()

        # split out switches
        switches = []
        if args and len(args) > 1 and args[0] == "/":
            # we have a switch, or a set of switches. These end with a space.
            switches = args[1:].split(None, 1)
            if len(switches) > 1:
                switches, args = switches
                switches = switches.split('/')
            else:
                args = ""
                switches = switches[0].split('/')
        arglist = [arg.strip() for arg in args.split()]

        # check for arg1, arg2, ... = argA, argB, ... constructs
        lhs, rhs = args, None
        lhslist, rhslist = [arg.strip() for arg in args.split(',')], []
        if args and '=' in args:
            lhs, rhs = [arg.strip() for arg in args.split('=', 1)]
            lhslist = [arg.strip() for arg in lhs.split(',')]
            rhslist = [arg.strip() for arg in rhs.split(',')]

        # save to object properties:
        self.raw = raw
        self.switches = switches
        self.args = args.strip()
        self.arglist = arglist
        self.lhs = lhs
        self.lhslist = lhslist
        self.rhs = rhs
        self.rhslist = rhslist

        # if the class has the account_caller property set on itself, we make
        # sure that self.caller is always the account if possible. We also
        # create a special property "character" for the puppeted object, if
        # any. This is convenient for commands defined on the Account only.
        if hasattr(self, "account_caller") and self.account_caller:
            if utils.inherits_from(
                                   self.caller,
                                   "evennia.objects.objects.DefaultObject"
                                   ):
                # caller is an Object/Character
                self.character = self.caller
                self.caller = self.caller.account
            elif utils.inherits_from(
                                     self.caller,
                                     "evennia.accounts.accounts.DefaultAccount"
                                     ):
                # caller was already an Account
                self.character = self.caller.get_puppet(self.session)
            else:
                self.character = None


class CmdScore(MuxCommand):
    """
    List abilities

    Usage:
       score

    Displays a formatted chart showing all of your relevant statistics.
    """
    key = "score"
    aliases = ["sc"]
    lock = "cmd:all()"
    help_category = "General"

    def func(self):
        """implements the actual functionality"""

        caller = self.caller

        strength, dexterity, intelligence, wisdom, constitution, \
            hitpoints_current, hitpoints_maximum, mana_current, mana_maximum, \
            moves_current, moves_maximum, sex, race, died, kills, \
            maximum_damage, maximum_kill_experience, hitroll, \
            experience_total, experience_spent, damroll, gold, bank_balance, \
            armor_class, alignment, saving_throw, staff_position, \
            immortal_invisible, immortal_cloak, immortal_ghost, holy_light, \
            level, age, wimpy, items, weight = self.caller.get_score_info()

        unspent_experience = experience_total - experience_spent
        experience_to_level = experience_total
        experience_in_level = experience_total

        modified_strength = caller.get_modified_attribute(caller, "strength")
        modified_intelligence = caller.get_modified_attribute(
                                                              caller,
                                                              "intelligence"
                                                              )
        modified_wisdom = caller.get_modified_attribute(caller, "wisdom")
        modified_dexterity = caller.get_modified_attribute(caller, "dexterity")
        modified_constitution = caller.get_modified_attribute(
                                                              caller,
                                                              "constitution"
                                                              )

        hit_points_string = ("%s/%s" % (hitpoints_current, hitpoints_maximum))
        mana_string = ("%s/%s" % (mana_current, mana_maximum))
        moves_string = ("%s/%s" % (moves_current, moves_maximum))
        name_and_title = self.caller

        score = ""
        buffer = ("|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-"
                  "|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w="
                  "|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-"
                  "|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|x\n|w| "
                  "|cName: |W%-40s                        |w|\n|w| |cLevel: "
                  "|W%-15d         |cRace: |W%-10s         |cAge: |W%-3d    "
                  "  |w|\n" % (name_and_title, level, race, age))
        score = score + buffer

        if level > 101:
            buffer = ("|w| |cStaff Position: |w%-15s                      "
                      "|w|\n" % staff_position)
            score = score + buffer

        buffer = ("|C======================================================"
                  "===================|W\n|w| |cStr: |w%-2d(|G%-2d|c)       "
                  "|c       Hit Points: |w%-12s     |cWimpy: |w%-4d     |w|\n"
                  % (strength, modified_strength, hit_points_string, wimpy))
        score = score + buffer

        buffer = ("|w| |cInt: |w%-2d|c(|G%-2d|c)                    |cMana:"
                  " |w%-13s     |cDied: |r%-6d   |w|\n"
                  % (intelligence, modified_intelligence, mana_string, died))
        score = score + buffer

        buffer = ("|w| |cWis: |w%-2d|c(|G%-2d|c)                   |cMoves:"
                  " |w%-13s    |cKills: |w%-9d|w|\n"
                  % (wisdom, modified_wisdom, moves_string, kills))
        score = score + buffer

        buffer = ("|w| |cDex: |w%-2d|c(|G%-2d|c)           |cItems carried: "
                  "|w%-3d         |cMax Damage: |w%-9d|w|\n"
                  % (dexterity, modified_dexterity, items, maximum_damage))
        score = score + buffer

        buffer = ("|w| |cCon: |w%-2d|c(|G%-2d|c)          |cWeight carried: "
                  "|w%-4d      |cMax Kill Exp: |w%-9d|w|\n"
                  % (
                      constitution,
                      modified_constitution,
                      weight,
                      maximum_kill_experience
                     ))
        score = score + buffer

        buffer = ("|w| |cHitroll: |w%-3d           |cExp in level: |w%-9d  "
                  "|cUnspent Exp: |w%-9d|w|\n"
                  % (hitroll, experience_in_level, unspent_experience))
        score = score + buffer

        buffer = ("|w| |cDamroll: |w%-3d      |cExp to next level: |w%-15d "
                  "                 |w|\n"
                  % (damroll, experience_to_level))
        score = score + buffer

        buffer = ("|w| |cGold: |y%-9d        |cBank Balance: |y%-12d        "
                  "             |w|\n" % (gold, bank_balance))
        score = score + buffer

        buffer = ("|w| |C---------------------------------------------------"
                  "------------------ |w|\n")
        score = score + buffer

        buffer = ("|w| |cArmor Class: |w%-5d              |cAlignment: |w%-5d"
                  "                      |w|\n" % (armor_class, alignment))
        score = score + buffer

        buffer = ("|w| |cSaving throw: |w%-4d                           "
                  "                         |w|\n" % saving_throw)
        score = score + buffer

        if level > 101:
            buffer = ("|w| |cHoly Light: |w%-3d       |cInvis: |w%-3d     |c"
                      "Cloak: |w%-3d    |cGhost: |w%-3d |w|\n"
                      % (
                          holy_light,
                          immortal_invisible,
                          immortal_cloak,
                          immortal_ghost
                         ))
            score = score + buffer

        score = score + ("|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-"
                         "|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w="
                         "|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-"
                         "|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w=|c-|w="
                         "|c-|w=|c-|w=|c-|x")

        self.caller.msg(score)


class CmdCharCreate(MuxCommand):
    """
    create a new character

    Usage:
      charcreate <charname> [= desc]

    Create a new character, optionally giving it a description. You
    may use upper-case letters in the name - you will nevertheless
    always be able to access your character using lower-case letters
    if you want.
    """

    key = "charcreate"
    locks = "cmd:pperm(Player)"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """create the new character"""
        account = self.account
        if not self.args:
            self.msg("Usage: charcreate <charname> [= description]")
            return
        key = self.lhs
        desc = self.rhs

        race = yield("""=====================================================\
===========
                                     Infra- Detect
  ##  Race       Str Dex Int Wis Con vision Hidden Size Hated By
================================================================
   1  Human                            No     No     3   4 races
   2  Elf             +1  +1      -1  Yes    Yes     2  11 races
   3  Eldar               +1  +1  -1  Yes    Yes     2  11 races
   4  Halfelf         +1              Yes     No     3  10 races
   5  Drow            +1      +1      Yes    Yes     2   6 races
   6  Dwarf           -1          +1  Yes    Yes     2  12 races
   7  Halfdwarf                   +1  Yes     No     2  12 races
   8  Hobbit          +1          -1  Yes     No     2  12 races
   9  Ogre        +1  -1  -1      +1   No     No     5   8 races
  10  Orc         +1      -1      +1  Yes     No     4   8 races
  11  Lizardman   +1  +1  -1  -1  +1   No     No     3   0 races
  12  Gnome       -1  +1      +1  -1  Yes     No     2  10 races
  13  Halfkobold  -2  +3  -1  -2  -2  Yes     No     2   5 races
================================================================

Please select a race for your character by selecting the number corresponding
to your chosen race and hitting [Enter] (e.g. 7). Please note anything other
than an input of a number 1 through 13 will result in a selection of the
unenviable halfkobold race.\n\n""")

        if race.isdigit():
            race = int(race)
            if(race == 1):
                race = "human"
            elif(race == 2):
                race = "elf"
            elif(race == 3):
                race = "eldar"
            elif(race == 4):
                race = "halfelf"
            elif(race == 5):
                race = "drow"
            elif(race == 6):
                race = "dwarf"
            elif(race == 7):
                race = "halfdwarf"
            elif(race == 8):
                race = "hobbit"
            elif(race == 9):
                race = "ogre"
            elif(race == 10):
                race = "orc"
            elif(race == 11):
                race = "lizardman"
            elif(race == 12):
                race = "gnome"
            elif(race == 13):
                race = "halfkobold"
            else:
                self.msg("I warned you. You all heard me warn him. Enjoy your "
                         "halfkobold.\n\n")
                race = "halfkobold"
        else:
            self.msg("I warned you. You all heard me warn him. Enjoy your "
                     "halfkobold.\n\n")
            race = "halfkobold"

        self.msg("You have selected the race of %s for your character.\n\n"
                 % race)

        sex = yield("""Please select a sex for your character by selecting the number corresponding
to your chosen sex and hitting [Enter]: 0 Neuter, 1 Male, 2 Female. Default is
neuter, if you decide to try to be cute again here.\n\n""")

        if sex.isdigit():
            sex = int(sex)
            if(sex == 2):
                sex = "female"
            elif(sex == 1):
                sex = "male"
            elif(sex == 0):
                sex = "neuter"
            else:
                self.msg("I warned you. Enjoy your neuter. Neutrality? "
                         "Something.\n\n")
                sex = "neuter"
        else:
            self.msg("I warned you. Enjoy your neuter. Neutrality? "
                     "Something.\n\n")
            sex = "neuter"

        self.msg("You have selected the sex of %s for your character.\n\n"
                 % sex)

        charmax = _MAX_NR_CHARACTERS

        if not account.is_superuser and (
                                         account.db._playable_characters and
                                         len(account.db._playable_characters) >=
                                         charmax
                                         ):
            plural = "" if charmax == 1 else "s"
            self.msg("You may only create a maximum of %s character%s."
                     % (charmax, plural))
            return
        from evennia.objects.models import ObjectDB

        typeclass = settings.BASE_CHARACTER_TYPECLASS

        if ObjectDB.objects.filter(
                                   db_typeclass_path=typeclass,
                                   db_key__iexact=key
                                  ):
            # check if this Character already exists. Note that we are only
            # searching the base character typeclass here, not any child
            # classes.
            self.msg("|rA character named '|w%s|r' already exists.|n" % key)
            return

        # create the character
        start_location = ObjectDB.objects.get_id(settings.START_LOCATION)
        default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
        permissions = settings.PERMISSION_ACCOUNT_DEFAULT
        new_character = create.create_object(
                                             typeclass,
                                             key=key,
                                             location=start_location,
                                             home=default_home,
                                             permissions=permissions
                                            )

        # set up new character based on inputs
        new_character.db.race = race
        new_character.db.sex = sex

        # only allow creator (and developers) to puppet this char
        new_character.locks.add(
            "puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer);"
            "delete:id(%i) or perm(Admin)"
            % (new_character.id, account.id, account.id)
        )
        account.db._playable_characters.append(new_character)
        if desc:
            new_character.db.desc = desc
        elif not new_character.db.desc:
            new_character.db.desc = "This is a character."
        self.msg(
            "Created new character %s. Use |wic %s|n to enter the game as this"
            "character."
            % (new_character.key, new_character.key)
        )
        logger.log_sec(
            "Character Created: %s (Caller: %s, IP: %s)."
            % (new_character, account, self.session.address)
        )


class CmdInventory(MuxCommand):
    """
    view inventory
    Usage:
      inventory
      inv
    Shows your inventory.
    """

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"
    arg_regex = r"$"

    def func(self):
        """check inventory"""
        items = self.caller.contents
        if not items:
            string = "You are not carrying anything."
        else:
            from evennia.utils.ansi import raw as raw_ansi

            table = self.styled_table(border="header")
            for item in items:
                if not item.db.equipped:  # So equipped items don't show up.
                    table.add_row(
                        f"|C{item.name}|n",
                        "{}|n".format(utils.crop(raw_ansi(item.db.desc), width=50) or ""),
                    )
            string = f"|wYou are carrying:\n{table}"
        self.caller.msg(string)


class CmdLook(MuxCommand):
    """
    look at location or object
    Usage:
        look
        look <obj>
        look *<account>
    Observes your location or objects in your vicinity.
    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """
        Handle the looking.
        """
        caller = self.caller
        if not self.args:
            target = caller.location
            if not target:
                caller.msg("You have no location to look at!")
                return
        else:
            target = caller.search(self.args)
            if not target:
                return
        self.msg((caller.at_look(target), {"type": "look"}), options=None)

        # Check to see if the target is a character (or mobile), and if so
        # get and show their equipment.

        if target.db.eq_slots:

            equipment_table = target.get_equipment_table()

            if target == caller:
                name = "You are"
            else:
                name = ("%s is" % target.key)

            caller.msg("%s wearing:\n" % name)

            caller.msg(equipment_table)


class CmdDrop(MuxCommand):
    """
    drop something
    Usage:
        drop <obj>
    Lets you drop an object from your inventory into the
    location you are currently in.
    """

    key = "drop"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Implement command"""

        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        # Because the DROP command by definition looks for items
        # in inventory, call the search function using location = caller
        obj = caller.search(
            self.args,
            location=caller,
            nofound_string="You aren't carrying %s." % self.args,
            multimatch_string="You carry more than one %s:" % self.args,
        )
        if not obj:
            return

        # Check for the object being cursed to be undroppable.

        if not obj.access(caller, "drop"):
            if obj.db.get_err_msg:
                caller.msg(obj.db.get_err_msg)
            else:
                caller.msg("This object is cursed, and cannot be dropped.")
            return

        # Call the object script's at_before_drop() method.
        if not obj.at_before_drop(caller):
            return

        success = obj.move_to(caller.location, quiet=True)
        if not success:
            caller.msg("This couldn't be dropped.")
        else:
            caller.msg("You drop %s." % (obj.name,))
            caller.location.msg_contents("%s drops %s."
                                         % (caller.name, obj.name),
                                         exclude=caller)
            # Call the object script's at_drop() method.
            obj.at_drop(caller)


class CmdOpen(ObjManipCommand):
    """
    open a new exit from the current room
    Usage:
      openexit <new exit>[;alias;alias..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = <destination>
    Handles the creation of exits. If a destination is given, the exit
    will point there. The <return exit> argument sets up an exit at the
    destination leading back to the current room. Destination name
    can be given both as a #dbref and a name, if that name is globally
    unique.
    """

    key = "openexit"
    locks = "cmd:perm(open) or perm(Builder)"
    help_category = "Building"

    new_obj_lockstring = "control:id({id}) or perm(Admin);delete:id({id}) or perm(Admin)"
    # a custom member method to chug out exits and do checks

    def create_exit(
                    self,
                    exit_name,
                    location,
                    destination,
                    exit_aliases=None,
                    typeclass=None
                    ):
        """
        Helper function to avoid code duplication.
        At this point we know destination is a valid location
        """
        caller = self.caller
        string = ""
        # check if this exit object already exists at the location.
        # we need to ignore errors (so no automatic feedback)since we
        # have to know the result of the search to decide what to do.
        exit_obj = caller.search(
                                 exit_name,
                                 location=location,
                                 quiet=True,
                                 exact=True
                                )
        if len(exit_obj) > 1:
            # give error message and return
            caller.search(exit_name, location=location, exact=True)
            return None
        if exit_obj:
            exit_obj = exit_obj[0]
            if not exit_obj.destination:
                # we are trying to link a non-exit
                string = "'%s' already exists and is not an exit!\nIf you want to convert it "
                string += (
                    "to an exit, you must assign an object to the 'destination' property first."
                )
                caller.msg(string % exit_name)
                return None
            # we are re-linking an old exit.
            old_destination = exit_obj.destination
            if old_destination:
                string = "Exit %s already exists." % exit_name
                if old_destination.id != destination.id:
                    # reroute the old exit.
                    exit_obj.destination = destination
                    if exit_aliases:
                        [exit_obj.aliases.add(alias) for alias in exit_aliases]
                    string += " Rerouted its old destination '%s' to '%s' and changed aliases." % (
                        old_destination.name,
                        destination.name,
                    )
                else:
                    string += " It already points to the correct place."

        else:
            # exit does not exist before. Create a new one.
            lockstring = self.new_obj_lockstring.format(id=caller.id)
            if not typeclass:
                typeclass = settings.BASE_EXIT_TYPECLASS
            exit_obj = create.create_object(
                typeclass,
                key=exit_name,
                location=location,
                aliases=exit_aliases,
                locks=lockstring,
                report_to=caller,
            )
            if exit_obj:
                # storing a destination is what makes it an exit!
                exit_obj.destination = destination
                string = (
                    ""
                    if not exit_aliases
                    else " (aliases: %s)" % (", ".join([str(e) for e in exit_aliases]))
                )
                string = "Created new Exit '%s' from %s to %s%s." % (
                    exit_name,
                    location.name,
                    destination.name,
                    string,
                )
            else:
                string = "Error: Exit '%s' not created." % exit_name
        # emit results
        caller.msg(string)
        return exit_obj

    def func(self):
        """
        This is where the processing starts.
        Uses the ObjManipCommand.parser() for pre-processing
        as well as the self.create_exit() method.
        """
        caller = self.caller

        if not self.args or not self.rhs:
            string = "Usage: open <new exit>[;alias...][:typeclass][,<return exit>[;alias..][:typeclass]]] "
            string += "= <destination>"
            caller.msg(string)
            return

        # We must have a location to open an exit
        location = caller.location
        if not location:
            caller.msg("You cannot create an exit from a None-location.")
            return

        # obtain needed info from cmdline

        exit_name = self.lhs_objs[0]["name"]
        exit_aliases = self.lhs_objs[0]["aliases"]
        exit_typeclass = self.lhs_objs[0]["option"]
        dest_name = self.rhs

        # first, check so the destination exists.
        destination = caller.search(dest_name, global_search=True)
        if not destination:
            return

        # Create exit
        ok = self.create_exit(exit_name, location, destination, exit_aliases, exit_typeclass)
        if not ok:
            # an error; the exit was not created, so we quit.
            return
        # Create back exit, if any
        if len(self.lhs_objs) > 1:
            back_exit_name = self.lhs_objs[1]["name"]
            back_exit_aliases = self.lhs_objs[1]["aliases"]
            back_exit_typeclass = self.lhs_objs[1]["option"]
            self.create_exit(
                back_exit_name, destination, location, back_exit_aliases, back_exit_typeclass
            )


class CmdRepop(MuxCommand):
    """
    Repopulate an area in the MUD, or all areas in the MUD.

    Usage:
      repop <area>

    Returns the area argument to its initial configuration. With no argument,
    it will repopulate all areas.
    """

    key = "repop"
    locks = "cmd:perm(Admin)"
    arg_regex = r"\s|$"

    def func(self):
        """
        The main body of the area repopulating function.
        """
    
        caller = self.caller

        # If an area is given, get all objects that are tagged with the area
        # name.
        if self.args:

            objects_to_reset = search.search_tag(self.args,
                                                  category="area name")

            if not objects_to_reset:
                caller.msg("There are no objects in %s."
                           % self.args)
                return

        # Otherwise, get all objects.
        else:
            objects_to_reset = search.search_tag(category="area name")

        # iterate through and reset all objects
        for object in objects_to_reset:
            object.at_reset()

        if self.args:
            caller.msg("The %s area has been reset." % self.args)
        else:
            caller.msg("All areas have been reset.")

class CmdDestroy(MuxCommand):
    """
    permanently delete objects
    Usage:
       destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]
    Switches:
       override - The destroy command will usually avoid accidentally
                  destroying account objects. This switch overrides this safety.
       force - destroy without confirmation.
    Examples:
       destroy house, roof, door, 44-78
       destroy 5-10, flower, 45
       destroy/force north
    Destroys one or many objects. If dbrefs are used, a range to delete can be
    given, e.g. 4-10. Also the end points will be deleted. This command
    displays a confirmation before destroying, to make sure of your choice.
    You can specify the /force switch to bypass this confirmation.
    """

    key = "destroy"
    aliases = ["delete", "del"]
    switch_options = ("override", "force")
    locks = "cmd:perm(destroy) or perm(Builder)"
    help_category = "Building"

    confirm = True  # set to False to always bypass confirmation
    default_confirm = "yes"  # what to assume if just pressing enter (yes/no)

    def func(self):
        """Implements the command."""

        caller = self.caller
        delete = True

        if not self.args or not self.lhslist:
            caller.msg("Usage: destroy[/switches] [obj, obj2, obj3, [dbref-dbref],...]")
            delete = False

        def delobj(obj):
            # helper function for deleting a single object
            string = ""
            if not obj.pk:
                string = "\nObject %s was already deleted." % obj.db_key
            else:
                objname = obj.name
                if not (obj.access(caller, "control") or obj.access(caller, "delete")):
                    return "\nYou don't have permission to delete %s." % objname
                if obj.account and "override" not in self.switches:
                    return (
                        "\nObject %s is controlled by an active account. Use /override to delete anyway."
                        % objname
                    )
                if obj.dbid == int(settings.DEFAULT_HOME.lstrip("#")):
                    return (
                        "\nYou are trying to delete |c%s|n, which is set as DEFAULT_HOME. "
                        "Re-point settings.DEFAULT_HOME to another "
                        "object before continuing." % objname
                    )

                had_exits = hasattr(obj, "exits") and obj.exits
                had_objs = hasattr(obj, "contents") and any(
                    obj
                    for obj in obj.contents
                    if not (hasattr(obj, "exits") and obj not in obj.exits)
                )
                # do the deletion
                okay = obj.delete()
                if not okay:
                    string += (
                        "\nERROR: %s not deleted, probably because delete() returned False."
                        % objname
                    )
                else:
                    string += "\n%s was destroyed." % objname
                    if had_exits:
                        string += " Exits to and from %s were destroyed as well." % objname
                    if had_objs:
                        string += " Objects inside %s were moved to their homes." % objname
            return string

        objs = []
        for objname in self.lhslist:
            if not delete:
                continue

            if "-" in objname:
                # might be a range of dbrefs
                dmin, dmax = [utils.dbref(part, reqhash=False) for part in objname.split("-", 1)]
                if dmin and dmax:
                    for dbref in range(int(dmin), int(dmax + 1)):
                        obj = caller.search("#" + str(dbref))
                        if obj:
                            objs.append(obj)
                    continue
                else:
                    obj = caller.search(objname)
            else:
                obj = caller.search(objname)

            if obj is None:
                self.caller.msg(
                    " (Objects to destroy must either be local or specified with a unique #dbref.)"
                )
            elif obj not in objs:
                objs.append(obj)

        if objs and ("force" not in self.switches and type(self).confirm):
            confirm = "Are you sure you want to destroy "
            if len(objs) == 1:
                confirm += objs[0].get_display_name(caller)
            elif len(objs) < 5:
                confirm += ", ".join([obj.get_display_name(caller) for obj in objs])
            else:
                confirm += ", ".join(["#{}".format(obj.id) for obj in objs])
            confirm += " [yes]/no?" if self.default_confirm == "yes" else " yes/[no]"
            answer = ""
            answer = yield (confirm)
            answer = self.default_confirm if answer == "" else answer

            if answer and answer not in ("yes", "y", "no", "n"):
                caller.msg(
                    "Canceled: Either accept the default by pressing return or specify yes/no."
                )
                delete = False
            elif answer.strip().lower() in ("n", "no"):
                caller.msg("Canceled: No object was destroyed.")
                delete = False

        if delete:
            results = []
            for obj in objs:
                # All code under the if statement below added to 1) clean up equipped status on
                # equipment on mobiles being deleted, and 2) clean up equipment slots on 
                # equipment being deleted.
                if obj.db.character_type == "mobile":
                    if not all(wear_location == "" for wear_location in obj.db.eq_slots.values()):
                        for wear_location in obj.db.eq_slots:
                            if obj.db.eq_slots[wear_location]:
                                equipment = obj.db.eq_slots[wear_location]
                                equipment.db.equipped = False
                #elif obj.db.equipped:
                #    wearer = obj.location
                #    if hasattr(wearer, eq_slots):
                #        for wear_location in wearer.db.eq_slots:
                #            if wearer.db.eq_slots[wear_location] == obj:
                #               wearer.db.eq_slots[wear_location] = ""
                results.append(delobj(obj))

            if results:
                caller.msg("".join(results).strip())

class CmdLock(MuxCommand):
    """
    assign a lock definition to an object
    Usage:
      objectlock <object or *account>[ = <lockstring>]
      or
      objectlock[/switch] <object or *account>/<access_type>
    Switch:
      del - delete given access type
      view - view lock associated with given access type (default)
    If no lockstring is given, shows all locks on
    object.
    Lockstring is of the form
       access_type:[NOT] func1(args)[ AND|OR][ NOT] func2(args) ...]
    Where func1, func2 ... valid lockfuncs with or without arguments.
    Separator expressions need not be capitalized.
    For example:
       'get: id(25) or perm(Admin)'
    The 'get' lock access_type is checked e.g. by the 'get' command.
    An object locked with this example lock will only be possible to pick up
    by Admins or by an object with id=25.
    You can add several access_types after one another by separating
    them by ';', i.e:
       'get:id(25); delete:perm(Builder)'
    """

    key = "objectlock"
    aliases = ["olock"]
    locks = "cmd: perm(locks) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Sets up the command"""

        caller = self.caller
        if not self.args:
            string = (
                "Usage: lock <object>[ = <lockstring>] or lock[/switch] " "<object>/<access_type>"
            )
            caller.msg(string)
            return

        if "/" in self.lhs:
            # call of the form lock obj/access_type
            objname, access_type = [p.strip() for p in self.lhs.split("/", 1)]
            obj = None
            if objname.startswith("*"):
                obj = caller.search_account(objname.lstrip("*"))
            if not obj:
                obj = caller.search(objname)
                if not obj:
                    return
            has_control_access = obj.access(caller, "control")
            if access_type == "control" and not has_control_access:
                # only allow to change 'control' access if you have 'control' access already
                caller.msg("You need 'control' access to change this type of lock.")
                return

            if not (has_control_access or obj.access(caller, "edit")):
                caller.msg("You are not allowed to do that.")
                return

            lockdef = obj.locks.get(access_type)

            if lockdef:
                if "del" in self.switches:
                    obj.locks.delete(access_type)
                    string = "deleted lock %s" % lockdef
                else:
                    string = lockdef
            else:
                string = "%s has no lock of access type '%s'." % (obj, access_type)
            caller.msg(string)
            return

        if self.rhs:
            # we have a = separator, so we are assigning a new lock
            if self.switches:
                swi = ", ".join(self.switches)
                caller.msg(
                    "Switch(es) |w%s|n can not be used with a "
                    "lock assignment. Use e.g. "
                    "|wlock/del objname/locktype|n instead." % swi
                )
                return

            objname, lockdef = self.lhs, self.rhs
            obj = None
            if objname.startswith("*"):
                obj = caller.search_account(objname.lstrip("*"))
            if not obj:
                obj = caller.search(objname)
                if not obj:
                    return
            if not (obj.access(caller, "control") or obj.access(caller, "edit")):
                caller.msg("You are not allowed to do that.")
                return
            ok = False
            lockdef = re.sub(r"\'|\"", "", lockdef)
            try:
                ok = obj.locks.add(lockdef)
            except LockException as e:
                caller.msg(str(e))
            if "cmd" in lockdef.lower() and inherits_from(
                obj, "evennia.objects.objects.DefaultExit"
            ):
                # special fix to update Exits since "cmd"-type locks won't
                # update on them unless their cmdsets are rebuilt.
                obj.at_init()
            if ok:
                caller.msg("Added lock '%s' to %s." % (lockdef, obj))
            return

        # if we get here, we are just viewing all locks on obj
        obj = None
        if self.lhs.startswith("*"):
            obj = caller.search_account(self.lhs.lstrip("*"))
        if not obj:
            obj = caller.search(self.lhs)
        if not obj:
            return
        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg("You are not allowed to do that.")
            return
        caller.msg("\n".join(obj.locks.all()))

class CmdPut(MuxCommand):
    """
    Put something in a container.
    Usage:
      put <inventory obj> <=> <target>
    Puts an item from your inventory in a container,
    placing it in its inventory.
    """

    key = "put"
    rhs_split = ("=")
    locks = "cmd:perm(Builder) or (objattr(closed, False) and objattr(item_type, \"container\"))"
    arg_regex = r"\s|$"

    def func(self):
        """Implement put"""

        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("Usage: put <inventory object> = <target>")
            return
        to_put = caller.search(
            self.lhs,
            location=caller,
            nofound_string="You aren't carrying %s." % self.lhs,
            multimatch_string="You carry more than one %s:" % self.lhs,
        )
        target = caller.search(self.rhs)
        if not (to_put and target):
            return
        if target == caller:
            caller.msg("You keep %s to yourself." % to_put.key)
            return
        if not to_put.location == caller:
            caller.msg("You are not holding %s." % to_put.key)
            return

        # give object
        success = to_put.move_to(target, quiet=True)
        if not success:
            caller.msg("This could not be put there.")
        else:
            caller.msg("You put %s in %s." % (to_put.key, target.key))

class CmdTag(MuxCommand):
    """
    handles the tags of an object, defaults to objects in the room.
    Usage:
      tag[/del] <obj> [= <tag>[:<category>]]
      tag/search <tag>[:<category]
    Switches:
      global - attempts to set a tag on an object not in the room.
      search - return all objects with a given Tag
      del - remove the given tag. If no tag is specified,
            clear all tags on object.
    Manipulates and lists tags on objects. Tags allow for quick
    grouping of and searching for objects.  If only <obj> is given,
    list all tags on the object.  If /search is used, list objects
    with the given tag.
    The category can be used for grouping tags themselves, but it
    should be used with restrain - tags on their own are usually
    enough to for most grouping schemes.
    """

    key = "tag"
    aliases = ["tags"]
    options = ("search", "del", "global")
    locks = "cmd:perm(tag) or perm(Builder)"
    help_category = "Building"
    arg_regex = r"(/\w+?(\s|$))|\s|$"

    def func(self):
        """Implement the tag functionality"""

        if not self.args:
            self.caller.msg("Usage: tag[/switches] <obj> [= <tag>[:<category>]]")
            return
        if "search" in self.switches:
            # search by tag
            tag = self.args
            category = None
            if ":" in tag:
                tag, category = [part.strip() for part in tag.split(":", 1)]
            objs = search.search_tag(tag, category=category)
            nobjs = len(objs)
            if nobjs > 0:
                catstr = (
                    " (category: '|w%s|n')" % category
                    if category
                    else ("" if nobjs == 1 else " (may have different tag categories)")
                )
                matchstr = ", ".join(o.get_display_name(self.caller) for o in objs)

                string = "Found |w%i|n object%s with tag '|w%s|n'%s:\n %s" % (
                    nobjs,
                    "s" if nobjs > 1 else "",
                    tag,
                    catstr,
                    matchstr,
                )
            else:
                string = "No objects found with tag '%s%s'." % (
                    tag,
                    " (category: %s)" % category if category else "",
                )
            self.caller.msg(string)
            return
        if "del" in self.switches:
            # remove one or all tags
            obj = self.caller.search(self.lhs, global_search=True)
            if not obj:
                return
            if self.rhs:
                # remove individual tag
                tag = self.rhs
                category = None
                if ":" in tag:
                    tag, category = [part.strip() for part in tag.split(":", 1)]
                if obj.tags.get(tag, category=category):
                    obj.tags.remove(tag, category=category)
                    string = "Removed tag '%s'%s from %s." % (
                        tag,
                        " (category: %s)" % category if category else "",
                        obj,
                    )
                else:
                    string = "No tag '%s'%s to delete on %s." % (
                        tag,
                        " (category: %s)" % category if category else "",
                        obj,
                    )
            else:
                # no tag specified, clear all tags
                old_tags = [
                    "%s%s" % (tag, " (category: %s)" % category if category else "")
                    for tag, category in obj.tags.all(return_key_and_category=True)
                ]
                if old_tags:
                    obj.tags.clear()
                    string = "Cleared all tags from %s: %s" % (obj, ", ".join(sorted(old_tags)))
                else:
                    string = "No Tags to clear on %s." % obj
            self.caller.msg(string)
            return
        # no search/deletion, global search
        if "global" in self.switches:
            if self.rhs:
                # = is found; command args are of the form obj = tag
                obj = self.caller.search(self.lhs, global_search=True)
                if not obj:
                    return
                tag = self.rhs
                category = None
                if ":" in tag:
                    tag, category = [part.strip() for part in tag.split(":", 1)]
                # create the tag
                obj.tags.add(tag, category=category)
                string = "Added tag '%s'%s to %s." % (
                    tag,
                    " (category: %s)" % category if category else "",
                    obj,
                )
                self.caller.msg(string)
            else:
                # no = found - list tags on object
                obj = self.caller.search(self.args, global_search=True)
                if not obj:
                    return
                tagtuples = obj.tags.all(return_key_and_category=True)
                ntags = len(tagtuples)
                tags = [tup[0] for tup in tagtuples]
                categories = [" (category: %s)" % tup[1] if tup[1] else "" for tup in tagtuples]
                if ntags:
                    string = "Tag%s on %s: %s" % (
                        "s" if ntags > 1 else "",
                        obj,
                        ", ".join(sorted("'%s'%s" % (tags[i], categories[i]) for i in range(ntags))),
                    )
                else:
                    string = "No tags attached to %s." % obj
                self.caller.msg(string)
        else:
            # Standard default tagging in room.
            if self.rhs:
                # = is found; command args are of the form obj = tag
                obj = self.caller.search(self.lhs, global_search=False)
                if not obj:
                    return
                tag = self.rhs
                category = None
                if ":" in tag:
                    tag, category = [part.strip() for part in tag.split(":", 1)]
                # create the tag
                obj.tags.add(tag, category=category)
                string = "Added tag '%s'%s to %s." % (
                    tag,
                    " (category: %s)" % category if category else "",
                    obj,
                )
                self.caller.msg(string)
            else:
                # no = found - list tags on object
                obj = self.caller.search(self.args, global_search=False)
                if not obj:
                    return
                tagtuples = obj.tags.all(return_key_and_category=True)
                ntags = len(tagtuples)
                tags = [tup[0] for tup in tagtuples]
                categories = [" (category: %s)" % tup[1] if tup[1] else "" for tup in tagtuples]
                if ntags:
                    string = "Tag%s on %s: %s" % (
                        "s" if ntags > 1 else "",
                        obj,
                        ", ".join(sorted("'%s'%s" % (tags[i], categories[i]) for i in range(ntags))),
                    )
                else:
                    string = "No tags attached to %s." % obj
                self.caller.msg(string)

class CmdSetHome(MuxCommand):
    """
    set an object's home location
    Usage:
      sethome <obj> [= <home_location>]
      sethom <obj>
    Switches:
      global - attempts to set home on an object not in the room.
    The "home" location is a "safety" location for objects; they
    will be moved there if their current location ceases to exist. All
    objects should always have a home location for this reason.
    It is also a convenient target of the "home" command.
    If no location is given, just view the object's home location.
    """

    key = "sethome"
    locks = "cmd:perm(sethome) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """implement the command"""
        if not self.args:
            string = "Usage: sethome <obj> [= <home_location>]"
            self.caller.msg(string)
            return

        if "global" in self.switches:
            obj = self.caller.search(self.lhs, global_search=True)
        else:
            obj = self.caller.search(self.lhs, global_search=False)
        if not obj:
            return
        if not self.rhs:
            # just view
            home = obj.home
            if not home:
                string = "This object has no home location set!"
            else:
                string = "%s's current home is %s(%s)." % (obj, home, home.dbref)
        else:
            # set a home location
            if "global" in self.switches:
                new_home = self.caller.search(self.rhs, global_search=True)
            else:
                new_home = self.caller.search(self.rhs, global_search=False)
            if not new_home:
                return
            old_home = obj.home
            obj.home = new_home
            if old_home:
                string = "Home location of %s was changed from %s(%s) to %s(%s)." % (
                    obj,
                    old_home,
                    old_home.dbref,
                    new_home,
                    new_home.dbref,
                )
            else:
                string = "Home location of %s was set to %s(%s)." % (obj, new_home, new_home.dbref)
        self.caller.msg(string)

class CmdTalk(MuxCommand):
    """
    Talk to a mobile to see what they have to say.
    Usage:
      talk <mobile>
    Talks to a mobile.
    """

    key = "talk"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Implement talk"""

        caller = self.caller
        if not self.args:
            caller.msg("Who do you want to talk to?")
            return

        to_talk = caller.search(
            self.args,
            location=caller.location,
            nofound_string="There is no %s here." % self.args,
            multimatch_string="There is more than one %s here:" % self.args,
        )

        if to_talk == caller:
            caller.msg("You mutter away to yourself quietly.")
            return
        if not to_talk.is_typeclass("typeclasses.characters.Mobile"):
            caller.msg("Try talking to a mobile.")
            return
        else:
            if to_talk.db.character_type != "mobile":
                caller.msg("Talk cannot be used on other players. Try say or tell.")
                return
            else:
                # Talk to the mobile.
                if to_talk.db.talk:
                    caller.msg('You strike up a conversation with %s.\n%s says, "%s"' % (to_talk.key, (to_talk.key[0].upper() + to_talk.key[1:]), to_talk.db.talk))
                else:
                    caller.msg("%s chatters along about nothing for a while." % to_talk.key)

class CmdInspect(MuxCommand):
    """
    Look more closely at an aspect of a room, object or mobile.
    Usage:
      inspect <room aspect>
      inspect <object> = <object aspect>
      inspect <mobile> = <mobile aspect>
    Looks at extra descriptions that are on rooms, objects or mobiles.
    """

    key = "inspect"
    rhs_split = ("=")
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Implement inspect"""

        caller = self.caller
        if not self.args:
            caller.msg("Usage: inspect <room aspect> OR inspect <object> = <object aspect>")
            return

        if not self.rhs:
            room = caller.location
            for extra_keywords_string in room.db.extra_description:
                extra_keywords_list = extra_keywords_string.split()
                if self.args in extra_keywords_list:
                    caller.msg("You inspect the %s:\n%s" % (self.args, room.db.extra_description[extra_keywords_string]))
                    return

            caller.msg("You see nothing special about the %s." % self.args)
            return
        else:
            object = caller.search(self.lhs, location=(caller or caller.location))
            aspect = self.rhs

            if not object:
                caller.msg("There is no %s here." % self.lhs)
            else:
                for extra_keywords_string in object.db.extra_descriptions:
                    extra_keywords_list = extra_keywords_string.split()
                    if self.rhs in extra_keywords_list:
                        caller.msg("You closely inpsect the %s on the %s:\n%s" % (self.rhs, self.lhs, object.db.extra_descriptions[extra_keywords_string]))
                        return
                caller.msg("You see nothing special about the %s on the %s." % (self.rhs, self.lhs))
                return
