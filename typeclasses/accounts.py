"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from evennia import DefaultAccount, DefaultGuest
from evennia.utils.utils import is_iter
from server.conf import settings

_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS

class Account(DefaultAccount):
    """
    This class describes the actual OOC account (i.e. the user connecting
    to the MUD). It does NOT have visual appearance in the game world (that
    is handled by the character which is connected to this). Comm channels
    are attended/joined using this object.

    It can be useful e.g. for storing configuration options for your game, but
    should generally not hold any character-related info (that's best handled
    on the character level).

    Can be set using BASE_ACCOUNT_TYPECLASS.


    * available properties

     key (string) - name of account
     name (string)- wrapper for user.username
     aliases (list of strings) - aliases to the object. Will be saved to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     user (User, read-only) - django User authorization object
     obj (Object) - game object controlled by account. 'character' can also be used.
     sessions (list of Sessions) - sessions connected to this account
     is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not create a database entry when storing data
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().

    * Helper methods

     msg(text=None, **kwargs)
     execute_cmd(raw_string, session=None)
     search(ostring, global_search=False, attribute_name=None, use_nicks=False, location=None, ignore_errors=False, account=False)
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False)
     check_permstring(permstring)

    * Hook methods (when re-implementation, remember methods need to have self as first arg)

     basetype_setup()
     at_account_creation()

     - note that the following hooks are also found on Objects and are
       usually handled on the character level:

     at_init()
     at_cmdset_get(**kwargs)
     at_first_login()
     at_post_login(session=None)
     at_disconnect()
     at_message_receive()
     at_message_send()
     at_server_reload()
     at_server_shutdown()

    """

    def at_look(self, target=None, session=None, **kwargs):
        """
        Called when this object executes a look. It allows to customize
        just what this means.
        Args:
            target (Object or list, optional): An object or a list
                objects to inspect.
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).
        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)
        """

        if target and not is_iter(target):
            # single target - just show it
            if hasattr(target, "return_appearance"):
                return target.return_appearance(self)
            else:
                return _("{target} has no in-game appearance.").format(target=target)
        else:
            # list of targets - make list to disconnect from db
            characters = list(tar for tar in target if tar) if target else []
            sessions = self.sessions.all()
            if not sessions:
                # no sessions, nothing to report
                return ""
            is_su = self.is_superuser

            # text shown when looking in the ooc area
            result = [f"Echoes of Creation\nOut-of-Character Menu for Account |g{self.key}|n"]

            nsess = len(sessions)
            result.append(
                nsess == 1
                and "\n\n|wYour current connected session:|n"
                or f"\n\n|wYour current connected sessions ({nsess}):|n"
            )
            for isess, sess in enumerate(sessions):
                csessid = sess.sessid
                addr = "%s (%s)" % (
                    sess.protocol_key,
                    isinstance(sess.address, tuple) and str(sess.address[0]) or str(sess.address),
                )
                result.append(
                    "\n %s %s"
                    % (
                        session
                        and session.sessid == csessid
                        and "|w* %s|n" % (isess + 1)
                        or "  %s" % (isess + 1),
                        addr,
                    )
                )

            charmax = _MAX_NR_CHARACTERS

            if characters:
                string_s_ending = len(characters) > 1 and "s" or ""
                result.append("\n\n To enter Echoes of Creation in-character, type |w ic <character>|n \nwith any of your below characters:")
                if is_su:
                    result.append(
                        f"\n\nAvailable character{string_s_ending} ({len(characters)}/unlimited):"
                    )
                else:
                    result.append(
                        "\n\nAvailable character%s%s:"
                        % (
                            string_s_ending,
                            charmax > 1 and " (%i/%i)" % (len(characters), charmax) or "",
                        )
                    )

                for char in characters:
                    csessions = char.sessions.all()
                    if csessions:
                        for sess in csessions:
                            # character is already puppeted
                            sid = sess in sessions and sessions.index(sess) + 1
                            if sess and sid:
                                result.append(
                                    f"\n - |G{char.key}|n [{', '.join(char.permissions.all())}] (played by you in session {sid})"
                                )
                            else:
                                result.append(
                                    f"\n - |R{char.key}|n [{', '.join(char.permissions.all())}] (played by someone else)"
                                )
                    else:
                        # character is "free to puppet"
                        result.append(f"\n - |Y{char.key}|n [{', '.join(char.permissions.all())}]")

            result.append("\n\n |wooc|n - entered in-game will return to this out-of-character menu")
            result.append("\n |whelp|n - to view more commands")
            result.append("\n |wpublic <Text>|n - talk on public channel")

            if is_su or len(characters) < charmax:
                if not characters:
                    result.append(
                        (
                            "\n\n You don't have any characters yet. See |whelp charcreate|n for creating one."
                        )
                    )
                else:
                    result.append("\n |wcharcreate <name> [=description]|n - create new character")
                    result.append(
                        "\n |wchardelete <name>|n - delete a character (cannot be undone!)"
                    )

            look_string = ("-" * 68) + "\n" + "".join(result) + "\n" + ("-" * 68)
            return look_string



class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
