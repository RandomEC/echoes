from evennia import create_object
from evennia import TICKER_HANDLER as tickerhandler
from commands.command import MuxCommand
from typeclasses.objects import Object
from world import rules_combat


class Combat(Object):
    """
    
    This is the class for instances of combat in rooms of the MUD.
    
    """

    def at_object_creation(self):
        self.db.combatants = {}
        self.db.rounds = 0
        self.x = 1
        tickerhandler.add(2, self.at_repeat)

    def at_stop(self):
        # Called just before the script is stopped/destroyed.
        for combatant in list(self.db.combatants.keys()):
            # note: the list() call above disconnects list from database,
            # needed because you are going to be removing things from the
            # combatants dictionary.
            self._cleanup_combatant(combatant)

    def msg_all(self, message):
        "Send message to all combatants"
        for combatant in self.db.combatants:
            self.db.combatants[combatant]["combatant"].msg(message)

    def allow_attacks(self, combatant, target):
        """
        Checks whether the combatant and target for this round are still alive, returns
        True if so, False if not.

        """
        if "mobile" in combatant.tags.all():
            if combatant.hitpoints_current <= 0:
                return False
        elif "mobile" in target.tags.all():
            if target.hitpoints_current <= 0:
                return False
        if "player" in combatant.tags.all():
            if combatant.hitpoints_current <= 0:
                return False
        elif "player" in target.tags.all():
            if target.hitpoints_current <= 0:
                return False

        return True

    def at_repeat(self):
        self.clear_messages()

        # Iterate through combatants to do a round of attacks.
        for combatant in self.db.combatants:

            # Make sure this combatant and target are alive.
            if self.allow_attacks(combatant, self.db.combatants[combatant]["target"]):
                attacker = self.db.combatants[combatant]["combatant"]
                victim = self.db.combatants[combatant]["target"]

                # Do the attacks for this attacker, and get output.
                attacker_string, victim_string, room_string = rules_combat.do_one_character_attacks(attacker, victim)

                # Add output to the rest of the output generated this round
                self.db.combatants[attacker]["combat message"] += attacker_string
                self.db.combatants[victim]["combat message"] += victim_string

                # For everyone in the combat that was not the attacker or victim, give them their output.
                for combatant in self.db.combatants:
                    if combatant != attacker and combatant != victim:
                        self.db.combatants[combatant]["combat message"] += room_string

        # Generate output for everyone for the above round. Anyone that died this round is still in
        # self.db.combatants at this point.
        for combatant in self.db.combatants:
            if "player" in combatant.tags.all():
                combat_message = self.db.combatants[combatant]["combat message"]
                target = self.db.combatants[combatant]["target"]

                # If the player and their target are still alive, tell them the status of their target.
                if combatant.hitpoints_current > 0 and target.hitpoints_current > 0:
                    combat_message += ("%s %s\n" % ((target.key[0].upper() + target.key[1:]), rules_combat.get_health_string(target)))
                combatant.msg(combat_message)

            # Check to see if the combatant is dead.
            if combatant.hitpoints_current <= 0:

                # Remove dead combatants from combat.
                self.remove_combatant(combatant)
                if "player" in combatant.tags.all():

                    # Reset dead players to one hitpoint, and move to home. Mobile hitpoints will get reset by reset
                    # function.
                    combatant.db.hitpoints["damaged"] = (combatant.hitpoints_maximum - 1)
                    combatant.move_to(combatant.home, quiet=True)

        # Check to see whether everyone in the combat is on the "same side" (player or mobile), and
        # end the combat.
        combatant_list = list(self.db.combatants.keys())
        # Check to see what type of combatant the first one is.
        if "mobile" in combatant_list[0].tags.all():
            first_combatant_type = "mobile"
        else:
            first_combatant_type = "player"
        # Default is to end the combat.
        combat_end = True

        # Cycle through combatants, and check their type.
        for combatant in combatant_list:
            if "mobile" in combatant.tags.all():
                combatant_type = "mobile"
            else:
                combatant_type = "player"

            # Check against first one. If any are different, set combat_end to False, and stop looking.
            if combatant_type != first_combatant_type:
                combat_end = False
                break;

        if combat_end == True:
            self.at_stop()
            self.delete()

        self.db.rounds += 1

    def clear_messages(self):
        for combatant in self.db.combatants:
            self.db.combatants[combatant]["combat message"] = ""

    def _init_combatant(self, combatant):
        """
        This initializes handler back-reference.        
        """
        combatant.ndb.combat_handler = self

    # Combat-handler methods

    def add_combatant(self, combatant, combatant_target):
        # Add combatant to handler
        self.db.combatants[combatant] = {"combatant": combatant, "target": combatant_target, "combat message": ""}

        # set up back-reference
        self._init_combatant(combatant)

    def _cleanup_combatant(self, combatant):
        """
        Remove combatant from handler and clean
        it of the back-reference.
        """
        del self.db.combatants[combatant]
        del combatant.ndb.combat_handler
        
    def remove_combatant(self, combatant):
        "Remove combatant from handler"
        if combatant in self.db.combatants:
            self._cleanup_combatant(combatant)

class CmdAttack(MuxCommand):
    """
    Start combat against a mobile target.
    Usage:
      attack <mobile>
    Starts the default attacks rounds that occur in combat.
    """

    key = "attack"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def create_combat(self, attacker, victim):
        """Create a combat, if needed"""
        combat = create_object("commands.combat_commands.Combat", key=("combat_handler_%s" % attacker.location.db.vnum))
        combat.add_combatant(attacker, victim)
        combat.add_combatant(victim, attacker)
        combat.location = attacker.location
        combat.db.desc = "This is a combat instance."
        combat.at_repeat()

    def func(self):
        """Implement attack"""

        attacker = self.caller
        if not self.args:
            attacker.msg("Usage: attack <mobile>")
            return

        victim = attacker.search(self.args, location=attacker.location)
        if not victim:
            attacker.msg("There is no %s here to attack." % self.args)
            return
        elif "player" in victim.tags.all():
            attacker.msg("You cannot attack another player!")
            return

        if attacker.db.combat_handler or victim.db.combat_handler:
            pass
        else:
            self.create_combat(attacker, victim)
